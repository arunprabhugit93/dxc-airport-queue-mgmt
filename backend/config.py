"""Shared configuration constants for the DXC Airport Queue Management POC.

THE single source of truth for every numeric/structural constant used by the
ETL, the ML training, the API, the SimPy engine, and the tests. All values are
frozen in `architecture/data-contract.md` (D2, D3, D4, D8). Never duplicate a
literal that lives here — import it.

Units:
- service / arrival rates: passengers per minute
- wait / duration values: minutes
- splits / weights: fractions in [0, 1]
"""

from __future__ import annotations

import os
from datetime import datetime

# --------------------------------------------------------------------------- #
# Enums (frozen — data-contract.md "Enums")
# --------------------------------------------------------------------------- #
AIRPORT_CODES: list[str] = ["ATL", "DEN", "ORD", "LAX", "DFW"]

# Queue area types. Real TSA data populates the two SECURITY_* areas; the Kaggle
# simulation populates CHECKIN / GATE / BAGGAGE.
AREA_TYPES: list[str] = [
    "SECURITY_TSA",
    "SECURITY_PRECHECK",
    "CHECKIN",
    "GATE",
    "BAGGAGE",
    "IMMIGRATION",
]
SECURITY_AREAS: list[str] = ["SECURITY_TSA", "SECURITY_PRECHECK"]
OPS_AREAS: list[str] = ["CHECKIN", "GATE", "BAGGAGE", "IMMIGRATION"]

SLA_STATUSES: list[str] = ["OK", "WARNING", "BREACH"]
SEVERITIES: list[str] = ["LOW", "MEDIUM", "HIGH"]
MODEL_NAMES: list[str] = ["prophet", "nbeats", "lstm"]
DETECTORS: list[str] = ["ecod", "iforest", "hst", "stl", "zscore"]
ANOMALY_TYPES: list[str] = ["SPIKE", "DROP", "CROSS_AIRPORT", "SEASONAL"]

# --------------------------------------------------------------------------- #
# Airport reference (frozen lat/lon — data-contract.md). lane_caps per checkpoint.
# --------------------------------------------------------------------------- #
AIRPORTS: dict[str, dict] = {
    "ATL": {
        "name": "Hartsfield-Jackson Atlanta",
        "lat": 33.6407,
        "lon": -84.4277,
        "lane_caps": {"SECURITY_TSA": 12, "SECURITY_PRECHECK": 4},
        "terminals": ["T-North", "T-South"],
    },
    "DEN": {
        "name": "Denver International",
        "lat": 39.8561,
        "lon": -104.6737,
        "lane_caps": {"SECURITY_TSA": 12, "SECURITY_PRECHECK": 4},
        "terminals": ["Jeppesen", "Concourse A", "Concourse B", "Concourse C"],
    },
    "ORD": {
        "name": "Chicago O'Hare",
        "lat": 41.9742,
        "lon": -87.9073,
        "lane_caps": {"SECURITY_TSA": 12, "SECURITY_PRECHECK": 4},
        "terminals": ["Terminal 1", "Terminal 2", "Terminal 3", "Terminal 5"],
    },
    "LAX": {
        "name": "Los Angeles International",
        "lat": 33.9416,
        "lon": -118.4085,
        "lane_caps": {"SECURITY_TSA": 12, "SECURITY_PRECHECK": 4},
        "terminals": ["TBIT", "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"],
    },
    "DFW": {
        "name": "Dallas/Fort Worth",
        "lat": 32.8998,
        "lon": -97.0403,
        "lane_caps": {"SECURITY_TSA": 12, "SECURITY_PRECHECK": 4},
        "terminals": ["Terminal A", "Terminal B", "Terminal C", "Terminal D", "Terminal E"],
    },
}

# --------------------------------------------------------------------------- #
# Queue math + disaggregation constants (frozen — data-contract.md)
# --------------------------------------------------------------------------- #
# Per-lane service rate (pax / min / lane). PreCheck is ~2x faster.
SERVICE_RATE_PER_LANE: dict[str, float] = {
    "SECURITY_TSA": 3.0,
    "SECURITY_PRECHECK": 6.0,
}

# Fraction of each hour's pax flowing to each security area.
CHECKPOINT_SPLIT: dict[str, float] = {
    "SECURITY_TSA": 0.80,
    "SECURITY_PRECHECK": 0.20,
}

# Physical lane caps per checkpoint (staffing bound).
LANE_CAPS: dict[str, int] = {
    "SECURITY_TSA": 12,
    "SECURITY_PRECHECK": 4,
}

# --------------------------------------------------------------------------- #
# SLA / alerting thresholds (frozen — D8)
# --------------------------------------------------------------------------- #
SLA_TARGET_MIN: float = 10.0
WARN_WAIT_MIN: float = 8.0
BREACH_WAIT_MIN: float = 10.0

# --------------------------------------------------------------------------- #
# Staffing constants (frozen — D4-B)
# --------------------------------------------------------------------------- #
OFFICERS_PER_LANE: int = 2

# --------------------------------------------------------------------------- #
# Demo clock (D1 / D7). Seeded to a known surge date so the demo story is
# repeatable: the day before US Thanksgiving 2021, where a synthetic spike is
# injected by the anomaly stage. Override with the DEMO_NOW env var.
# --------------------------------------------------------------------------- #
_DEFAULT_DEMO_NOW = "2021-11-24 07:00:00"
DEMO_NOW: datetime = datetime.fromisoformat(
    os.environ.get("DEMO_NOW", _DEFAULT_DEMO_NOW)
)

# --------------------------------------------------------------------------- #
# Hourly disaggregation weights (frozen — data-contract.md).
# 24 fractions of daily pax by hour, bimodal (AM + PM peaks), sum == 1.0.
#   00-03  zero (airport effectively closed to screening)
#   04     ramp
#   05-08  AM peak  (~0.07 each)
#   09-15  midday plateau (~0.04 each)
#   16-19  PM peak  (~0.06 each)
#   20-23  taper
# Built so the raw weights sum to exactly 1.0 after normalisation.
# --------------------------------------------------------------------------- #
def _build_hourly_weights() -> list[float]:
    raw = [
        0.000, 0.000, 0.000, 0.000,  # 00-03 closed
        0.020,                        # 04 ramp
        0.070, 0.072, 0.073, 0.070,  # 05-08 AM peak
        0.045, 0.043, 0.041, 0.040,  # 09-12 midday
        0.040, 0.041, 0.043,         # 13-15 midday
        0.060, 0.062, 0.061, 0.058,  # 16-19 PM peak
        0.035, 0.025, 0.018, 0.010,  # 20-23 taper
    ]
    total = sum(raw)
    weights = [w / total for w in raw]
    # Correct any float drift so sum is exactly 1.0.
    weights[8] += 1.0 - sum(weights)
    return weights


HOURLY_WEIGHTS: list[float] = _build_hourly_weights()

assert len(HOURLY_WEIGHTS) == 24, "HOURLY_WEIGHTS must have 24 entries"
assert abs(sum(HOURLY_WEIGHTS) - 1.0) < 1e-9, "HOURLY_WEIGHTS must sum to 1.0"

# --------------------------------------------------------------------------- #
# Filesystem paths (relative to projects/dxc-poc/). Consumers should resolve
# these against the package root via pathlib.
# --------------------------------------------------------------------------- #
DUCKDB_FILENAME: str = "airport.duckdb"

# TSA data window (matches the real ERAU FOIA window: 974 daily obs / airport).
TSA_START_DATE: str = "2020-02-15"
TSA_END_DATE: str = "2022-10-15"

# Ops (Kaggle stand-in) window.
OPS_START_DATE: str = "2020-02-15"
OPS_END_DATE: str = "2022-10-15"
OPS_OPEN_HOUR: int = 5
OPS_CLOSE_HOUR: int = 23

# Forecast horizons written to queue_predictions (minutes ahead).
FORECAST_HORIZONS_MIN: list[int] = [15, 30, 45, 60, 90, 120]

# Global RNG seed for all synthetic generation.
RANDOM_SEED: int = 42
