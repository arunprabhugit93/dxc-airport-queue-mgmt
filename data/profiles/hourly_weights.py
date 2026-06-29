"""Re-export of the frozen HOURLY_WEIGHTS disaggregation vector.

Thin convenience module so the disaggregation step can import the profile from
its conventional location (`data/profiles/`) while config.py remains the single
source of truth. Do not redefine the weights here.
"""

from __future__ import annotations

from backend.config import HOURLY_WEIGHTS

__all__ = ["HOURLY_WEIGHTS"]
