"""Master ETL runner. Run this to (re)build airport.duckdb from scratch.

Usage: python -m data.etl.run_etl  (from projects/dxc-poc/)

Executes the pipeline in dependency order. Every step is idempotent (it checks
for existing data and skips if present), so re-running is safe and fast. Progress
is printed to stdout with timestamps (this is the one module allowed to use print
rather than logging, since it is the human-facing entry point).
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure the package root (projects/dxc-poc/) is importable when run as a script
# or as a module, and when invoked from the Docker WORKDIR /app.
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from data.etl import (  # noqa: E402
    create_schema,
    disaggregate,
    generate_ops_data,
    generate_tsa_data,
    train_models,
)


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _step(label: str, fn) -> None:
    print(f"[{_ts()}] >>> {label} ...", flush=True)
    start = time.time()
    result = fn()
    elapsed = time.time() - start
    print(f"[{_ts()}] <<< {label} done in {elapsed:.1f}s  ({result})", flush=True)


def main() -> None:
    # Keep library logging visible but quiet third-party noise.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
    logging.getLogger("prophet").setLevel(logging.WARNING)

    print(f"[{_ts()}] ===== DXC Airport POC — ETL build start =====", flush=True)
    print(f"[{_ts()}] DuckDB target: {create_schema.DB_PATH}", flush=True)

    _step("1/5 create schema", create_schema.create_all)
    _step("2/5 generate TSA daily data", generate_tsa_data.run)
    _step("3/5 disaggregate to checkpoint-hour", disaggregate.run)
    _step("4/5 generate ops (Kaggle stand-in) data", generate_ops_data.run)
    _step("5/5 train models + write predictions/anomalies/staffing", train_models.run)

    print(f"[{_ts()}] ===== ETL build complete =====", flush=True)


if __name__ == "__main__":
    main()
