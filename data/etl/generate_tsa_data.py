"""Synthetic TSA daily throughput generator (realistic, seeded stand-in).

Real TSA FOIA / ERAU downloads need credentials and are flaky in CI, so this
module deterministically synthesises the same *shape* as the real 2020-2022 TSA
FOIA series: 974 daily rows per airport (2020-02-15 -> 2022-10-15) with weekly
seasonality, US-holiday spikes, the spring-2020 COVID trough, and a sigmoid
recovery. It also emits the ERAU-style regressors (`mobility_index`,
`covid_cases`, `is_holiday`) used by the Prophet model.

To swap in real data instead, see `download_real_data.md`. All randomness is
seeded (numpy seed 42) so the build is reproducible.

Writes one `grain='daily'` row per airport-date into `tsa_throughput`.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from backend import config

logger = logging.getLogger(__name__)

PACKAGE_ROOT: Path = Path(__file__).resolve().parents[2]
DB_PATH: Path = PACKAGE_ROOT / "data" / config.DUCKDB_FILENAME

# Base normal-period daily pax range per airport (matches briefing 2A figures).
_BASE_PAX: dict[str, tuple[int, int]] = {
    "ATL": (75_000, 95_000),
    "DEN": (55_000, 75_000),
    "ORD": (60_000, 80_000),
    "LAX": (65_000, 85_000),
    "DFW": (65_000, 85_000),
}

# Weekday multipliers (Mon=0 .. Sun=6). Fri/Sun peaks ~20% above Mon/Tue troughs.
_WEEKDAY_MULT: dict[int, float] = {
    0: 0.95,  # Mon
    1: 0.90,  # Tue (trough)
    2: 0.94,  # Wed
    3: 1.02,  # Thu
    4: 1.12,  # Fri (peak)
    5: 0.98,  # Sat
    6: 1.10,  # Sun (peak)
}


def _us_holidays(years: list[int]) -> dict[date, float]:
    """Return {date: surge_multiplier} for major US travel holidays.

    Surges are applied to the holiday and a small window around it (the real
    travel peak is the day before/after, not always the day itself).
    """
    holidays: dict[date, float] = {}

    def add_window(center: date, peak: float, span: int = 2) -> None:
        for d in range(-span, span + 1):
            day = center + timedelta(days=d)
            # Strongest on the eve/return days, tapering out.
            mult = 1.0 + (peak - 1.0) * (1.0 - abs(d) / (span + 1))
            holidays[day] = max(holidays.get(day, 1.0), mult)

    for y in years:
        # July 4th
        add_window(date(y, 7, 4), 1.45)
        # Memorial Day = last Monday of May
        may_last = date(y, 5, 31)
        while may_last.weekday() != 0:
            may_last -= timedelta(days=1)
        add_window(may_last, 1.40)
        # Labor Day = first Monday of September
        sep = date(y, 9, 1)
        while sep.weekday() != 0:
            sep += timedelta(days=1)
        add_window(sep, 1.40)
        # Thanksgiving = 4th Thursday of November (heaviest travel of year)
        nov = date(y, 11, 1)
        thursdays = [nov + timedelta(days=i) for i in range(30)
                     if (nov + timedelta(days=i)).weekday() == 3
                     and (nov + timedelta(days=i)).month == 11]
        add_window(thursdays[3], 1.50, span=3)
        # Christmas / New Year window
        add_window(date(y, 12, 23), 1.45, span=3)
        add_window(date(y, 12, 31), 1.35, span=2)
    return holidays


def _covid_factor(d: date) -> float:
    """Multiplier capturing COVID collapse + sigmoid recovery (0..1.0+)."""
    # Deep trough: 2020-03-15 .. 2020-06-30 -> ~10-20% of normal.
    trough_start = date(2020, 3, 15)
    trough_end = date(2020, 6, 30)
    if d < trough_start:
        return 1.0  # pre-COVID normal
    if trough_start <= d <= trough_end:
        # Sharp drop into the trough, hold near ~0.13.
        frac = (d - trough_start).days / max((trough_end - trough_start).days, 1)
        return 1.0 - 0.87 * min(frac * 3.0, 1.0)
    # Recovery: sigmoid from ~0.13 back toward ~1.0.
    # Reach ~85% by Jan 2021, ~100% by Jan 2022.
    days_into_recovery = (d - trough_end).days
    # Sigmoid centred ~120 days post-trough.
    sig = 1.0 / (1.0 + np.exp(-(days_into_recovery - 120) / 70.0))
    return 0.13 + (1.0 - 0.13) * sig


def _covid_cases(d: date) -> int:
    """Synthetic national COVID case count: peaks Nov 2020 and Jan 2021."""
    peaks = [
        (date(2020, 11, 25), 180_000, 45),  # fall 2020 wave
        (date(2021, 1, 10), 250_000, 50),   # winter peak
        (date(2021, 9, 1), 160_000, 60),    # delta
        (date(2022, 1, 15), 800_000, 35),   # omicron
    ]
    total = 0.0
    for center, height, width in peaks:
        delta_days = (d - center).days
        total += height * np.exp(-(delta_days ** 2) / (2 * width ** 2))
    return int(max(total, 0))


def _already_loaded(con: duckdb.DuckDBPyConnection) -> bool:
    n = con.execute(
        "SELECT COUNT(*) FROM tsa_throughput WHERE grain = 'daily'"
    ).fetchone()[0]
    return n > 0


def run(db_path: Path | None = None) -> int:
    """Generate and insert daily TSA rows. Idempotent. Returns rows written."""
    np.random.seed(config.RANDOM_SEED)
    path = db_path or DB_PATH

    start = date.fromisoformat(config.TSA_START_DATE)
    end = date.fromisoformat(config.TSA_END_DATE)
    n_days = (end - start).days + 1
    dates = [start + timedelta(days=i) for i in range(n_days)]
    years = sorted({d.year for d in dates})
    holidays = _us_holidays(years)

    logger.info("Generating %d daily rows/airport over %d days", n_days, n_days)

    with duckdb.connect(str(path)) as con:
        if _already_loaded(con):
            existing = con.execute(
                "SELECT COUNT(*) FROM tsa_throughput WHERE grain='daily'"
            ).fetchone()[0]
            logger.info("Daily TSA data already present (%d rows); skipping", existing)
            return 0

        records: list[dict] = []
        for code in config.AIRPORT_CODES:
            lo, hi = _BASE_PAX[code]
            base = (lo + hi) / 2.0
            amp = (hi - lo) / 2.0
            for d in dates:
                covid = _covid_factor(d)
                weekday = _WEEKDAY_MULT[d.weekday()]
                holiday_mult = holidays.get(d, 1.0)
                is_holiday = d in holidays
                # Mild annual seasonality (summer travel bump).
                doy = d.timetuple().tm_yday
                seasonal = 1.0 + 0.06 * np.sin(2 * np.pi * (doy - 80) / 365.0)
                noise = 1.0 + np.random.uniform(-0.05, 0.05)
                pax = base * weekday * holiday_mult * covid * seasonal * noise
                # Small within-band variation around the base centre.
                pax += np.random.uniform(-amp, amp) * 0.15 * covid
                pax = int(max(pax, 0))

                cases = _covid_cases(d)
                # Mobility index inversely tracks COVID severity, correlates w/ pax.
                mobility = float(np.clip(
                    covid * 100.0 + np.random.uniform(-4, 4), 5.0, 115.0
                ))

                records.append(
                    {
                        "airport_code": code,
                        "obs_date": d,
                        "obs_hour": None,
                        "area_type": None,
                        "grain": "daily",
                        "pax": pax,
                        "lanes_open": None,
                        "wait_min_est": None,
                        "mobility_index": round(mobility, 2),
                        "covid_cases": cases,
                        "is_holiday": is_holiday,
                        "source": "derived",
                    }
                )

        df = pd.DataFrame.from_records(records)
        # Enforce contract column order so positional INSERT matches the DDL.
        df = df[[
            "airport_code", "obs_date", "obs_hour", "area_type", "grain", "pax",
            "lanes_open", "wait_min_est", "mobility_index", "covid_cases",
            "is_holiday", "source",
        ]]
        con.execute(
            """
            INSERT INTO tsa_throughput
            SELECT airport_code, obs_date,
                   CAST(obs_hour AS INTEGER), CAST(area_type AS VARCHAR), grain, pax,
                   CAST(lanes_open AS INTEGER), CAST(wait_min_est AS DOUBLE),
                   mobility_index, covid_cases, is_holiday, source
            FROM df
            """
        )
        logger.info("Inserted %d daily TSA rows", len(df))
        return len(df)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
