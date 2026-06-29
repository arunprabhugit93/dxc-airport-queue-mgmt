"""Thin wrapper around the FastAPI backend, with Streamlit caching."""

from __future__ import annotations

import os
from datetime import date

import requests
import streamlit as st

API_BASE: str = os.environ.get("API_BASE", "http://localhost:8000")

SLA_COLOUR = {"OK": "#2EA043", "WARNING": "#D29922", "BREACH": "#F85149"}
SEVERITY_COLOUR = {"LOW": "#636B74", "MEDIUM": "#D29922", "HIGH": "#F85149"}
AIRPORT_CODES = ["ATL", "DEN", "ORD", "LAX", "DFW"]

AREA_TYPES = [
    "CHECKIN", "SECURITY_TSA", "SECURITY_PRECHECK",
    "IMMIGRATION", "GATE", "BAGGAGE",
]

AREA_LABELS = {
    "CHECKIN": "Check-in",
    "SECURITY_TSA": "Security (TSA)",
    "SECURITY_PRECHECK": "Security (PreCheck)",
    "IMMIGRATION": "Immigration",
    "GATE": "Gate",
    "BAGGAGE": "Baggage Claim",
}

DATA_MIN_DATE = date(2020, 2, 15)
DATA_MAX_DATE = date(2022, 10, 15)

COST_PER_STAFF_HOUR = 35.0


def _friendly_error(resp: requests.Response) -> str:
    """Extract a readable error from an API error response."""
    try:
        body = resp.json()
        detail = body.get("detail", "")
        if isinstance(detail, str) and detail:
            return detail
        if isinstance(detail, list) and detail:
            return "; ".join(d.get("msg", str(d)) for d in detail)
        return str(body)
    except Exception:
        return resp.text[:200] if resp.text else f"HTTP {resp.status_code}"


def _get(path: str, params: dict | None = None) -> dict:
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=15)
    except requests.ConnectionError:
        raise ConnectionError("Cannot reach API. Is the backend running on port 8000?")
    if not r.ok:
        raise RuntimeError(_friendly_error(r))
    return r.json()


def _post(path: str, json: dict) -> dict:
    try:
        r = requests.post(f"{API_BASE}{path}", json=json, timeout=30)
    except requests.ConnectionError:
        raise ConnectionError("Cannot reach API. Is the backend running on port 8000?")
    if not r.ok:
        raise RuntimeError(_friendly_error(r))
    return r.json()


# ---------------------------------------------------------------------------
# Existing endpoint wrappers
# ---------------------------------------------------------------------------


@st.cache_data(ttl=30)
def get_clock() -> dict:
    return _get("/config/clock")


def set_clock(demo_now: str) -> dict:
    get_clock.clear()
    return _post("/config/clock", {"demo_now": demo_now})


@st.cache_data(ttl=30)
def get_airports(_demo_now: str) -> dict:
    return _get("/airports")


@st.cache_data(ttl=30)
def get_queues_current(_demo_now: str, airport: str | None = None) -> dict:
    params = {}
    if airport and airport != "All":
        params["airport"] = airport
    return _get("/queues/current", params or None)


@st.cache_data(ttl=30)
def get_forecast(
    _demo_now: str,
    airport: str,
    horizon: int = 60,
    area: str = "SECURITY_TSA",
    model: str = "prophet",
) -> dict:
    return _get("/queues/forecast", {
        "airport": airport, "horizon": horizon, "area": area, "model": model,
    })


@st.cache_data(ttl=30)
def get_anomalies(
    _demo_now: str, airport: str | None = None, hours: int = 24,
) -> dict:
    params: dict = {"hours": hours}
    if airport and airport not in ("All", "ALL"):
        params["airport"] = airport
    return _get("/anomalies/recent", params)


@st.cache_data(ttl=30)
def get_staffing(
    _demo_now: str, airport: str, date_str: str, area: str = "SECURITY_TSA",
    sla_target: float = 10.0,
) -> dict:
    return _get("/staffing/recommend", {
        "airport": airport, "date": date_str, "area": area, "sla_target": sla_target,
    })


@st.cache_data(ttl=30)
def get_kpis(_demo_now: str, date_from: str, date_to: str, airport: str = "ALL") -> dict:
    params: dict = {"date_from": date_from, "date_to": date_to}
    if airport and airport != "All":
        params["airport"] = airport
    return _get("/dashboard/kpis", params)


@st.cache_data(ttl=30)
def get_models() -> dict:
    return _get("/models")


def simulate_what_if(body: dict) -> dict:
    return _post("/simulate/what-if", body)


def get_health() -> dict:
    return _get("/health")


# ---------------------------------------------------------------------------
# NEW endpoint wrappers (graceful fallback if not yet available)
# ---------------------------------------------------------------------------


@st.cache_data(ttl=30)
def get_all_area_queues(_demo_now: str, airport: str) -> dict | None:
    """Fetch queue state for ALL areas. Returns None if endpoint unavailable."""
    try:
        return _get("/queues/all-areas", {"airport": airport})
    except Exception:
        return None


@st.cache_data(ttl=30)
def get_passenger_journey(_demo_now: str, airport: str) -> dict | None:
    """Fetch passenger journey stages. Returns None if endpoint unavailable."""
    try:
        return _get("/passenger-journey", {"airport": airport})
    except Exception:
        return None


@st.cache_data(ttl=30)
def get_recommendations(_demo_now: str, airport: str | None = None) -> dict | None:
    """Fetch operations recommendations. Returns None if endpoint unavailable."""
    try:
        params = {}
        if airport and airport not in ("All", "ALL"):
            params["airport"] = airport
        return _get("/operations/recommendations", params or None)
    except Exception:
        return None


@st.cache_data(ttl=30)
def get_heatmap(
    _demo_now: str, airport: str, area: str = "SECURITY_TSA", days: int = 30,
) -> dict | None:
    """Fetch hourly heatmap data. Returns None if endpoint unavailable."""
    try:
        return _get("/queues/heatmap", {
            "airport": airport, "area": area, "days": days,
        })
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def check_high_anomalies(demo_now: str, airport: str | None = None) -> list[dict]:
    try:
        data = get_anomalies(demo_now, airport=airport, hours=2)
        return [e for e in data.get("events", []) if e.get("severity") == "HIGH"]
    except Exception:
        return []


def sla_badge_html(status: str) -> str:
    """Return an HTML badge span for an SLA status value."""
    colour = SLA_COLOUR.get(status, "#636B74")
    return (
        f'<span style="background:{colour};color:#fff;padding:3px 10px;'
        f'border-radius:4px;font-size:0.75em;font-weight:600;letter-spacing:0.03em;">{status}</span>'
    )


def trend_arrow(trend: str) -> str:
    """Return a coloured trend arrow string."""
    if trend == "UP":
        return '<span style="color:#F85149;font-weight:700;">&#9650; UP</span>'
    if trend == "DOWN":
        return '<span style="color:#2EA043;font-weight:700;">&#9660; DOWN</span>'
    return '<span style="color:#636B74;font-weight:700;">&#9654; FLAT</span>'


def severity_badge_html(severity: str) -> str:
    """Return an HTML badge span for a severity value."""
    colour = SEVERITY_COLOUR.get(severity, "#636B74")
    return (
        f'<span style="background:{colour};color:#fff;padding:3px 10px;'
        f'border-radius:4px;font-size:0.75em;font-weight:600;letter-spacing:0.03em;">{severity}</span>'
    )


def priority_badge_html(priority: str) -> str:
    """Return an HTML badge for recommendation priority."""
    colour_map = {"HIGH": "#F85149", "MEDIUM": "#D29922", "LOW": "#2EA043"}
    colour = colour_map.get(priority.upper(), "#636B74")
    return (
        f'<span style="background:{colour};color:#fff;padding:3px 10px;'
        f'border-radius:4px;font-size:0.75em;font-weight:600;letter-spacing:0.03em;">{priority}</span>'
    )


def render_sidebar() -> tuple[str, str]:
    """Render the global sidebar controls. Returns (selected_airport, demo_now)."""
    from theme import t, BLUE_PRIMARY

    with st.sidebar:
        p = t()

        # Brand header
        st.markdown(
            f'<div style="padding:8px 0 16px 0;margin-bottom:8px;'
            f'border-bottom:1px solid {p["border"]};">'
            f'<div style="font-size:1.2em;font-weight:800;color:{p["text_primary"]};'
            f'letter-spacing:0.03em;">Airport Ops</div>'
            f'<div style="font-size:0.7em;color:{p["text_muted"]};margin-top:2px;">'
            f'Queue Management Intelligence</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Airport selector
        st.markdown(
            f'<div style="font-size:0.7em;color:{p["text_muted"]};text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-bottom:4px;">Select Airport</div>',
            unsafe_allow_html=True,
        )
        airport = st.selectbox("Airport", ["All"] + AIRPORT_CODES, index=0,
                               key="sb_airport", label_visibility="collapsed")

        st.divider()

        # Demo clock
        st.markdown(
            f'<div style="font-size:0.7em;color:{p["text_muted"]};text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-bottom:6px;">Demo Clock</div>',
            unsafe_allow_html=True,
        )
        try:
            clock = get_clock()
            demo_now = clock["demo_now"]
        except Exception:
            demo_now = "2021-11-24T07:00:00"
            st.warning("API unreachable")

        st.markdown(
            f'<div style="background:{p["surface"]};border:1px solid {p["border"]};'
            f'border-radius:8px;padding:12px 14px;margin-bottom:10px;">'
            f'<div style="font-size:0.65em;color:{p["text_muted"]};text-transform:uppercase;'
            f'letter-spacing:0.06em;">Current Time</div>'
            f'<div style="font-size:1em;color:{BLUE_PRIMARY};font-weight:700;'
            f'font-family:monospace;margin-top:4px;">{demo_now}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            new_date = st.date_input(
                "Date", value=None, key="clock_date",
                min_value=DATA_MIN_DATE, max_value=DATA_MAX_DATE,
            )
        with col2:
            new_time = st.time_input("Time", value=None, key="clock_time")

        if st.button("Set Clock", key="sb_set_clock"):
            if new_date and new_time:
                ts = f"{new_date}T{new_time.strftime('%H:%M:%S')}"
                try:
                    result = set_clock(ts)
                    demo_now = result["demo_now"]
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not set clock: {e}")
            else:
                st.warning("Pick date and time first.")

        st.markdown(
            f'<div style="font-size:0.7em;color:{p["text_muted"]};margin-top:4px;">'
            f'Range: {DATA_MIN_DATE} to {DATA_MAX_DATE}</div>',
            unsafe_allow_html=True,
        )

    return airport, demo_now


@st.cache_data(ttl=30)
def get_shift_handoff(_demo_now: str, airport: str | None = None, shift_hours: int = 8) -> dict | None:
    try:
        params: dict = {"shift_hours": shift_hours}
        if airport and airport not in ("All", "ALL"):
            params["airport"] = airport
        return _get("/operations/shift-handoff", params)
    except Exception:
        return None


@st.cache_data(ttl=30)
def get_airport_terminals(_demo_now: str, airport_code: str) -> dict | None:
    try:
        return _get(f"/airports/{airport_code}/terminals")
    except Exception:
        return None


@st.cache_data(ttl=30)
def get_network_health(_demo_now: str) -> dict | None:
    try:
        return _get("/network/health")
    except Exception:
        return None


@st.cache_data(ttl=30)
def get_capacity(_demo_now: str, airport_code: str) -> dict | None:
    try:
        return _get(f"/airports/{airport_code}/capacity")
    except Exception:
        return None


@st.cache_data(ttl=30)
def get_scorecard(_demo_now: str, airport_code: str, target_date: str | None = None) -> dict | None:
    try:
        params = {}
        if target_date:
            params["target_date"] = target_date
        return _get(f"/airports/{airport_code}/scorecard", params or None)
    except Exception:
        return None


def render_theme_toggle() -> None:
    """Render a light/dark theme toggle in the top-right corner of the page."""
    mode = st.session_state.get("theme_mode", "dark")
    _, col_toggle = st.columns([8, 1])
    with col_toggle:
        new_mode = st.toggle(
            "Light" if mode == "dark" else "Dark",
            value=(mode == "light"),
            key="topbar_theme",
        )
        target = "light" if new_mode else "dark"
        if target != mode:
            st.session_state["theme_mode"] = target
            st.rerun()


def render_alert_banner(demo_now: str, airport: str | None = None) -> None:
    """Show prominent alert banners for high-severity anomalies."""
    high = check_high_anomalies(demo_now, airport if airport != "All" else None)
    for event in high[:3]:
        desc = event.get("description", "High-severity anomaly detected")
        st.markdown(
            f'<div style="background:#F8514915;border:1px solid #F85149;border-left:4px solid #F85149;'
            f'border-radius:8px;padding:12px 16px;margin-bottom:8px;">'
            f'<span style="color:#F85149;font-weight:700;font-size:0.8em;letter-spacing:0.05em;">'
            f'ALERT</span>'
            f'<span style="color:#FAFAFA;margin-left:10px;">{desc}</span></div>',
            unsafe_allow_html=True,
        )
