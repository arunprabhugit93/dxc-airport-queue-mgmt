"""Page 6 -- Staff & Lane Optimizer."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api_client import (
    COST_PER_STAFF_HOUR,
    DATA_MIN_DATE,
    DATA_MAX_DATE,
    render_alert_banner,
    render_sidebar,
    get_staffing,
)

st.set_page_config(page_title="Staff & Lane Optimizer", layout="wide", page_icon="✈️")
airport, demo_now = render_sidebar()

st.title("Staff & Lane Optimizer")
st.caption("AI-driven staffing recommendations to meet SLA targets while optimising costs")
render_alert_banner(demo_now, airport)

selected = airport if airport != "All" else "ATL"

with st.sidebar:
    st.divider()
    rec_date = st.date_input(
        "Staffing date", value=None, key="staffing_date",
        min_value=DATA_MIN_DATE, max_value=DATA_MAX_DATE,
    )
    area = st.selectbox(
        "Checkpoint", ["SECURITY_TSA", "SECURITY_PRECHECK"], key="staffing_area",
    )
    sla_target = st.slider(
        "SLA target (min)", 5.0, 20.0, 10.0, step=0.5, key="staffing_sla",
    )
    run_btn = st.button("Recommend", key="staffing_btn")

if not run_btn or not rec_date:
    st.info(
        f"Select a date ({DATA_MIN_DATE} to {DATA_MAX_DATE}) and click "
        f"**Recommend** in the sidebar."
    )
    st.stop()

try:
    data = get_staffing(demo_now, selected, str(rec_date), area, sla_target)
except Exception as e:
    st.error(f"API error: {e}")
    st.stop()

hours = data.get("hours", [])
totals = data.get("totals", {})

if not hours:
    st.warning("No staffing data for this date.")
    st.stop()

# ---------------------------------------------------------------------------
# Summary KPI cards
# ---------------------------------------------------------------------------
peak_lanes = totals.get("peak_lanes", 0)
total_staff_hours = totals.get("total_staff_hours", 0)
sla_met_count = sum(1 for h in hours if h.get("sla_met"))
sla_compliance = round((sla_met_count / len(hours)) * 100, 1) if hours else 100.0
estimated_cost = total_staff_hours * COST_PER_STAFF_HOUR

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Peak Lanes", peak_lanes)
c2.metric("Total Staff-Hours", total_staff_hours)
c3.metric("SLA Compliance", f"{sla_compliance}%")
c4.metric("Hours Meeting SLA", f"{sla_met_count}/{len(hours)}")
c5.metric("Est. Daily Cost", f"${estimated_cost:,.0f}")

# Narrative
if sla_compliance < 100:
    gap_hours = [h for h in hours if not h.get("sla_met")]
    gap_times = [f"{h['rec_hour']:02d}:00" for h in gap_hours]
    st.warning(
        f"SLA target of {sla_target} min is NOT met during: {', '.join(gap_times)}. "
        f"Consider increasing lane count or adjusting shift schedules for these periods."
    )
else:
    st.success(
        f"All hours meet the SLA target of {sla_target} min. "
        f"Estimated daily cost: ${estimated_cost:,.0f}."
    )

# ---------------------------------------------------------------------------
# Schedule chart with shift boundaries
# ---------------------------------------------------------------------------
st.subheader("Staffing Schedule")
df = pd.DataFrame(hours)

fig = go.Figure()

# Bar colours: green for SLA met, red for not
colours = ["#2ecc71" if m else "#e74c3c" for m in df["sla_met"]]
fig.add_trace(go.Bar(
    x=df["rec_hour"], y=df["recommended_lanes"], name="Lanes",
    marker_color=colours,
    text=df["recommended_lanes"],
    textposition="auto",
))

fig.add_trace(go.Scatter(
    x=df["rec_hour"], y=df["forecast_pax"], name="Forecast Pax",
    yaxis="y2", mode="lines+markers",
    line=dict(color="#2980b9", width=2),
    marker=dict(size=5),
))

# Shift boundaries (8h shifts: 06-14, 14-22, 22-06)
for shift_start in [6, 14, 22]:
    fig.add_vline(
        x=shift_start, line_dash="dot", line_color="#95a5a6",
        annotation_text=f"Shift {shift_start:02d}:00",
        annotation_position="top",
    )

fig.update_layout(
    title=f"{selected} -- {area} Staffing ({rec_date})",
    xaxis_title="Hour",
    yaxis_title="Lanes",
    yaxis2=dict(title="Passengers", overlaying="y", side="right"),
    height=450,
    barmode="group",
    legend=dict(orientation="h", y=-0.15),
)
st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Gap Analysis -- hours where SLA not met
# ---------------------------------------------------------------------------
gap_hours_data = [h for h in hours if not h.get("sla_met")]
if gap_hours_data:
    st.subheader("SLA Gap Analysis")
    st.markdown("The following hours do NOT meet the SLA target:")
    for h in gap_hours_data:
        overshoot = h["expected_wait_min"] - sla_target
        st.markdown(
            f'<div style="border-left:4px solid #e74c3c;padding:8px 14px;'
            f'margin-bottom:6px;background:#e74c3c08;border-radius:2px;">'
            f'<strong>{h["rec_hour"]:02d}:00</strong> -- '
            f'Wait: {h["expected_wait_min"]:.1f} min '
            f'(+{overshoot:.1f} over target) | '
            f'{h["forecast_pax"]} pax | '
            f'{h["recommended_lanes"]} lanes</div>',
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Table + download
# ---------------------------------------------------------------------------
st.subheader("Hourly Schedule")
show_cols = [
    "rec_hour", "forecast_pax", "recommended_lanes", "recommended_staff",
    "expected_wait_min", "sla_met",
]
show_cols = [c for c in show_cols if c in df.columns]
st.dataframe(df[show_cols], width="stretch", hide_index=True)
st.download_button(
    "Download CSV", df[show_cols].to_csv(index=False), "staffing.csv", "text/csv",
)
