"""Creates all tables in airport.duckdb per data-contract.md. Idempotent.

Every table is created with `CREATE TABLE IF NOT EXISTS`, using the exact column
names, types, and NOT NULL constraints from the frozen data contract. The
reference table `airports_ref` is seeded from `backend.config.AIRPORTS`. Running
this repeatedly is safe and leaves existing data untouched.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from backend import config

logger = logging.getLogger(__name__)

# Package root = projects/dxc-poc/ (this file is data/etl/create_schema.py).
PACKAGE_ROOT: Path = Path(__file__).resolve().parents[2]
DB_PATH: Path = PACKAGE_ROOT / "data" / config.DUCKDB_FILENAME


# DDL is kept verbatim-aligned to data-contract.md so the test-engineer can
# assert column names/types directly.
_DDL: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS airports_ref (
        airport_code      VARCHAR NOT NULL,
        name              VARCHAR NOT NULL,
        lat               DOUBLE  NOT NULL,
        lon               DOUBLE  NOT NULL,
        lane_cap_tsa      INTEGER NOT NULL,
        lane_cap_precheck INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tsa_throughput (
        airport_code   VARCHAR NOT NULL,
        obs_date       DATE    NOT NULL,
        obs_hour       INTEGER,
        area_type      VARCHAR,
        grain          VARCHAR NOT NULL,
        pax            INTEGER NOT NULL,
        lanes_open     INTEGER,
        wait_min_est   DOUBLE,
        mobility_index DOUBLE,
        covid_cases    INTEGER,
        is_holiday     BOOLEAN,
        source         VARCHAR NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS airport_ops (
        airport_code  VARCHAR   NOT NULL,
        area_type     VARCHAR   NOT NULL,
        ts            TIMESTAMP NOT NULL,
        queue_length  INTEGER,
        throughput    INTEGER,
        wait_min      DOUBLE,
        staff_on_duty INTEGER,
        resource_id   VARCHAR,
        source        VARCHAR   NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS queue_predictions (
        airport_code    VARCHAR   NOT NULL,
        area_type       VARCHAR   NOT NULL,
        model_name      VARCHAR   NOT NULL,
        origin_ts       TIMESTAMP NOT NULL,
        horizon_min     INTEGER   NOT NULL,
        target_ts       TIMESTAMP NOT NULL,
        pred_wait_min   DOUBLE    NOT NULL,
        pred_throughput INTEGER,
        lower_min       DOUBLE,
        upper_min       DOUBLE,
        generated_at    TIMESTAMP NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS anomaly_events (
        event_id       BIGINT    NOT NULL,
        airport_code   VARCHAR   NOT NULL,
        area_type      VARCHAR,
        detected_at    TIMESTAMP NOT NULL,
        anomaly_type   VARCHAR   NOT NULL,
        detector       VARCHAR   NOT NULL,
        metric         VARCHAR   NOT NULL,
        observed_value DOUBLE    NOT NULL,
        expected_value DOUBLE,
        score          DOUBLE    NOT NULL,
        severity       VARCHAR   NOT NULL,
        description    VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS staffing_recommendations (
        airport_code      VARCHAR   NOT NULL,
        rec_date          DATE      NOT NULL,
        rec_hour          INTEGER   NOT NULL,
        area_type         VARCHAR   NOT NULL,
        forecast_pax      INTEGER   NOT NULL,
        recommended_lanes INTEGER   NOT NULL,
        recommended_staff INTEGER   NOT NULL,
        expected_wait_min DOUBLE    NOT NULL,
        sla_target_min    DOUBLE    NOT NULL,
        sla_met           BOOLEAN   NOT NULL,
        generated_at      TIMESTAMP NOT NULL
    )
    """,
]


def _seed_airports_ref(con: duckdb.DuckDBPyConnection) -> None:
    """Seed airports_ref from config.AIRPORTS (idempotent: clears then inserts)."""
    con.execute("DELETE FROM airports_ref")
    rows = []
    for code in config.AIRPORT_CODES:
        a = config.AIRPORTS[code]
        rows.append(
            (
                code,
                a["name"],
                a["lat"],
                a["lon"],
                a["lane_caps"]["SECURITY_TSA"],
                a["lane_caps"]["SECURITY_PRECHECK"],
            )
        )
    con.executemany(
        "INSERT INTO airports_ref VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    logger.info("Seeded airports_ref with %d airports", len(rows))


def create_all(db_path: Path | None = None) -> Path:
    """Create all contract tables and seed reference data. Returns the DB path."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Creating schema in %s", path)
    with duckdb.connect(str(path)) as con:
        for ddl in _DDL:
            con.execute(ddl)
        _seed_airports_ref(con)
    logger.info("Schema ready (%d tables)", len(_DDL))
    return path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    create_all()
