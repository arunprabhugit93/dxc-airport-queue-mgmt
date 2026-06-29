"""Deterministic daily -> checkpoint-hour disaggregation + M/M/c wait derivation.

For each `grain='daily'` row in `tsa_throughput`, this expands the daily pax
total into 24 hours x 2 security areas (SECURITY_TSA, SECURITY_PRECHECK) = 48
`grain='checkpoint_hour'` rows, using the frozen `HOURLY_WEIGHTS` and
`CHECKPOINT_SPLIT` constants. Lanes open and a modelled wait (`wait_min_est`)
are derived per the data contract:

  lanes_open  = max(2, min(LANE_CAPS[area], ceil(pax_hour / 300)))
  wait_min_est = M/M/c Wq(lambda=pax_hour/60, mu=SERVICE_RATE_PER_LANE, c=lanes)

The transform is purely deterministic (no RNG) so hourly sums reconcile exactly
to the daily total (the tested invariant), modulo integer rounding of the split.
`source='derived'` on every emitted row.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path

import duckdb
import pandas as pd

from backend import config
from backend.models.queue_math import mm_c_wait
from data.profiles.hourly_weights import HOURLY_WEIGHTS

logger = logging.getLogger(__name__)

PACKAGE_ROOT: Path = Path(__file__).resolve().parents[2]
DB_PATH: Path = PACKAGE_ROOT / "data" / config.DUCKDB_FILENAME

_PAX_PER_LANE_HEURISTIC: int = 300  # pax/hour/lane threshold for opening a lane
_MIN_LANES: int = 2


def _derive_lanes(pax_hour: int, area: str) -> int:
    """Lanes open for an hour: capped, floored at 2 when there's any demand."""
    if pax_hour <= 0:
        return 0
    cap = config.LANE_CAPS[area]
    return max(_MIN_LANES, min(cap, math.ceil(pax_hour / _PAX_PER_LANE_HEURISTIC)))


def _derive_wait(pax_hour: int, area: str, lanes: int) -> float:
    """M/M/c expected wait (min) for the hour, clamped to [0, 120]."""
    if pax_hour <= 0 or lanes <= 0:
        return 0.0
    lam = pax_hour / 60.0  # pax/min
    mu = config.SERVICE_RATE_PER_LANE[area]
    return round(mm_c_wait(lam, mu, lanes), 3)


def _already_done(con: duckdb.DuckDBPyConnection) -> bool:
    n = con.execute(
        "SELECT COUNT(*) FROM tsa_throughput WHERE grain = 'checkpoint_hour'"
    ).fetchone()[0]
    return n > 0


def run(db_path: Path | None = None) -> int:
    """Expand daily rows into checkpoint-hour rows. Idempotent. Returns rows added."""
    path = db_path or DB_PATH
    with duckdb.connect(str(path)) as con:
        if _already_done(con):
            existing = con.execute(
                "SELECT COUNT(*) FROM tsa_throughput WHERE grain='checkpoint_hour'"
            ).fetchone()[0]
            logger.info("Checkpoint-hour rows already present (%d); skipping", existing)
            return 0

        daily = con.execute(
            """
            SELECT airport_code, obs_date, pax, mobility_index, covid_cases, is_holiday
            FROM tsa_throughput
            WHERE grain = 'daily'
            ORDER BY airport_code, obs_date
            """
        ).fetchall()

        logger.info("Disaggregating %d daily rows into checkpoint-hour grain", len(daily))

        records: list[dict] = []
        for airport_code, obs_date, pax, mobility, cases, is_holiday in daily:
            for hour in range(24):
                hour_pax = pax * HOURLY_WEIGHTS[hour]
                for area in config.SECURITY_AREAS:
                    area_pax = int(round(hour_pax * config.CHECKPOINT_SPLIT[area]))
                    lanes = _derive_lanes(area_pax, area)
                    wait = _derive_wait(area_pax, area, lanes)
                    records.append(
                        {
                            "airport_code": airport_code,
                            "obs_date": obs_date,
                            "obs_hour": hour,
                            "area_type": area,
                            "grain": "checkpoint_hour",
                            "pax": area_pax,
                            "lanes_open": lanes,
                            "wait_min_est": wait,
                            "mobility_index": mobility,
                            "covid_cases": cases,
                            "is_holiday": is_holiday,
                            "source": "derived",
                        }
                    )

        df = pd.DataFrame.from_records(records)
        # Enforce contract column order to match the table definition.
        df = df[[
            "airport_code", "obs_date", "obs_hour", "area_type", "grain", "pax",
            "lanes_open", "wait_min_est", "mobility_index", "covid_cases",
            "is_holiday", "source",
        ]]
        con.execute("INSERT INTO tsa_throughput SELECT * FROM df")
        logger.info("Inserted %d checkpoint-hour rows", len(df))
        return len(df)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
