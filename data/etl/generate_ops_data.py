"""Synthetic airport-operations generator (Kaggle multi-table stand-in).

The real Kaggle "Airport Operations Multi-Table" dataset models a single major
hub and needs a Kaggle login to download. This module synthesises the same
queue-area coverage TSA data lacks (CHECKIN, GATE, BAGGAGE) for all 5 airports,
hourly over 2022-01-01 -> 2022-10-15 during operating hours (05:00-23:00).

The single Kaggle hub is mapped deterministically across the 5 airports (the
contract's "Kaggle hub mapped to one of the 5"). Queue length, wait, throughput,
and staffing follow the same intraday/weekly patterns as the TSA series. All
randomness seeded (numpy 42). Writes to `airport_ops` with `source='kaggle'`.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from backend import config
from data.profiles.hourly_weights import HOURLY_WEIGHTS

logger = logging.getLogger(__name__)

PACKAGE_ROOT: Path = Path(__file__).resolve().parents[2]
DB_PATH: Path = PACKAGE_ROOT / "data" / config.DUCKDB_FILENAME

# Per-area baseline scale: typical peak queue length and processing characteristics.
_AREA_PROFILE: dict[str, dict] = {
    "CHECKIN": {"peak_queue": 120, "base_wait": 12.0, "tput_scale": 90, "staff": (6, 18)},
    "GATE": {"peak_queue": 80, "base_wait": 6.0, "tput_scale": 70, "staff": (2, 8)},
    "BAGGAGE": {"peak_queue": 60, "base_wait": 8.0, "tput_scale": 60, "staff": (3, 10)},
    "IMMIGRATION": {"peak_queue": 100, "base_wait": 15.0, "tput_scale": 50, "staff": (4, 12)},
}

# Weekday multipliers (Mon=0..Sun=6), mirrors the TSA weekly shape.
_WEEKDAY_MULT: dict[int, float] = {
    0: 0.95, 1: 0.90, 2: 0.94, 3: 1.02, 4: 1.12, 5: 0.98, 6: 1.10,
}


def _already_loaded(con: duckdb.DuckDBPyConnection) -> bool:
    n = con.execute("SELECT COUNT(*) FROM airport_ops").fetchone()[0]
    return n > 0


def run(db_path: Path | None = None) -> int:
    """Generate and insert hourly ops rows. Idempotent. Returns rows written."""
    np.random.seed(config.RANDOM_SEED)
    path = db_path or DB_PATH

    start = date.fromisoformat(config.OPS_START_DATE)
    end = date.fromisoformat(config.OPS_END_DATE)
    n_days = (end - start).days + 1
    dates = [start + timedelta(days=i) for i in range(n_days)]
    hours = list(range(config.OPS_OPEN_HOUR, config.OPS_CLOSE_HOUR + 1))

    # Normalise hourly weights across operating hours so the busiest hour ~= 1.0.
    op_weights = np.array([HOURLY_WEIGHTS[h] for h in hours])
    op_weights = op_weights / op_weights.max()

    with duckdb.connect(str(path)) as con:
        if _already_loaded(con):
            existing = con.execute("SELECT COUNT(*) FROM airport_ops").fetchone()[0]
            logger.info("airport_ops already present (%d rows); skipping", existing)
            return 0

        logger.info(
            "Generating ops rows: %d airports x %d areas x %d days x %d hours",
            len(config.AIRPORT_CODES), len(config.OPS_AREAS), n_days, len(hours),
        )

        records: list[dict] = []
        for code in config.AIRPORT_CODES:
            for area in config.OPS_AREAS:
                prof = _AREA_PROFILE[area]
                staff_lo, staff_hi = prof["staff"]
                for d in dates:
                    wmult = _WEEKDAY_MULT[d.weekday()]
                    for hi, hour in enumerate(hours):
                        intensity = float(op_weights[hi]) * wmult
                        noise = 1.0 + np.random.uniform(-0.15, 0.15)
                        queue_len = int(max(0, prof["peak_queue"] * intensity * noise))
                        queue_len = int(np.clip(queue_len, 5, 150))
                        wait = float(np.clip(
                            prof["base_wait"] * intensity * noise
                            + np.random.uniform(0, 3),
                            1.0, 45.0,
                        ))
                        throughput = int(max(0, prof["tput_scale"] * intensity * noise * 10))
                        staff = int(np.clip(
                            staff_lo + (staff_hi - staff_lo) * intensity
                            + np.random.uniform(-1, 1),
                            staff_lo, staff_hi,
                        ))
                        ts = datetime(d.year, d.month, d.day, hour, 0, 0)
                        records.append(
                            {
                                "airport_code": code,
                                "area_type": area,
                                "ts": ts,
                                "queue_length": queue_len,
                                "throughput": throughput,
                                "wait_min": round(wait, 2),
                                "staff_on_duty": staff,
                                "resource_id": f"{area[:3]}-{code}-01",
                                "source": "kaggle",
                            }
                        )

        df = pd.DataFrame.from_records(records)
        df = df[[
            "airport_code", "area_type", "ts", "queue_length", "throughput",
            "wait_min", "staff_on_duty", "resource_id", "source",
        ]]
        con.execute("INSERT INTO airport_ops SELECT * FROM df")
        logger.info("Inserted %d ops rows", len(df))
        return len(df)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
