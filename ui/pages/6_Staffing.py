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
from theme import (
    inject_theme,
    section_header,
    metric_card,
    spacer,
    apply_chart_theme,
    SURFACE,
    BORDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    BLUE_PRIMARY,
    GREEN,
    YELLOW,
    RED,
)

st.set_page_config(page_title="Staff & Lane Optimizer", layout="wide")
inject_theme()
airport, demo_now = render_sidebar()

# Page header
st.markdown(
    '<h1 style="color:#FAFAFA;font-weight:700;margin-bottom:4px;">Staff & Lane Optimizer</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="color:#8B949E;font-size:0.95em;margin-bottom:24px;">'
    'AI-driven staffing recommendations to meet SLA targets while optimising costs</p>',
    unsafe_allow_html=True,
)
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
    st.markdown(
        f'<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;'
        f'padding:20px;text-align:center;">'
        f'<div style="color:{TEXT_SECONDARY};font-size:0.95em;">'
        f'Select a date ({DATA_MIN_DATE} to {DATA_MAX_DATE}) and click '
        f'<span style="color:{BLUE_PRIMARY};font-weight:600;">Recommend</span> in the sidebar.'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    st.stop()

try:
    data = get_staffing(demo_now, selected, str(rec_date), area, sla_target)
except Exception as e:
    st.error(f"API error: {e}")
    st.stop()

hours_data = data.get("hours", [])
totals = data.get("totals", {})

if not hours_data:
    st.warning("No staffing data for this date.")
    st.stop()

# ---------------------------------------------------------------------------
# Summary KPI cards
# ---------------------------------------------------------------------------
peak_lanes = totals.get("peak_lanes", 0)
total_staff_hours = totals.get("total_staff_hours", 0)
sla_met_count = sum(1 for h in hours_data if h.get("sla_met"))
sla_compliance = round((sla_met_count / len(hours_data)) * 100, 1) if hours_data else 100.0
estimated_cost = total_staff_hours * COST_PER_STAFF_HOUR

section_header("Staffing Summary")
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(metric_card("Peak Lanes", str(peak_lanes)), unsafe_allow_html=True)
with c2:
    st.markdown(metric_card("Total Staff-Hours", str(total_staff_hours)), unsafe_allow_html=True)
with c3:
    comp_color = GREEN if sla_compliance == 100 else YELLOW if sla_compliance >= 80 else RED
    st.markdown(metric_card("SLA Compliance", f"{sla_compliance}%", border_color=comp_color), unsafe_allow_html=True)
with c4:
    st.markdown(metric_card("Hours Meeting SLA", f"{sla_met_count}/{len(hours_data)}"), unsafe_allow_html=True)
with c5:
    st.markdown(metric_card("Est. Daily Cost", f"${estimated_cost:,.0f}"), unsafe_allow_html=True)

spacer(12)

# Narrative
if sla_compliance < 100:
    gap_hours = [h for h in hours_data if not h.get("sla_met")]
    gap_times = [f"{h['rec_hour']:02d}:00" for h in gap_hours]
    st.markdown(
        f'<div style="background:#D2992215;border:1px solid {YELLOW};border-left:4px solid {YELLOW};'
        f'border-radius:8px;padding:12px 16px;">'
        f'<span style="color:{YELLOW};font-weight:700;font-size:0.8em;letter-spacing:0.05em;">'
        f'GAP DETECTED</span>'
        f'<span style="color:{TEXT_PRIMARY};margin-left:10px;">'
        f'SLA target of {sla_target} min is NOT met during: {", ".join(gap_times)}. '
        f'Consider increasing lane count or adjusting shift schedules for these periods.</span></div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div style="background:#2EA04315;border:1px solid {GREEN};border-left:4px solid {GREEN};'
        f'border-radius:8px;padding:12px 16px;">'
        f'<span style="color:{GREEN};font-weight:700;font-size:0.8em;letter-spacing:0.05em;">'
        f'ON TARGET</span>'
        f'<span style="color:{TEXT_PRIMARY};margin-left:10px;">'
        f'All hours meet the SLA target of {sla_target} min. '
        f'Estimated daily cost: ${estimated_cost:,.0f}.</span></div>',
        unsafe_allow_html=True,
    )

spacer()

# ---------------------------------------------------------------------------
# Schedule chart with shift boundaries
# ---------------------------------------------------------------------------
section_header("Staffing Schedule")
df = pd.DataFrame(hours_data)

fig = go.Figure()

colours = [GREEN if m else RED for m in df["sla_met"]]
fig.add_trace(go.Bar(
    x=df["rec_hour"], y=df["recommended_lanes"], name="Lanes",
    marker=dict(color=colours, opacity=0.9, line=dict(color=BORDER, width=1)),
    text=df["recommended_lanes"],
    textposition="auto",
    textfont=dict(color=TEXT_PRIMARY),
))

fig.add_trace(go.Scatter(
    x=df["rec_hour"], y=df["forecast_pax"], name="Forecast Pax",
    yaxis="y2", mode="lines+markers",
    line=dict(color=BLUE_PRIMARY, width=2.5),
    marker=dict(size=6),
))

# Shift boundaries
for shift_start in [6, 14, 22]:
    fig.add_vline(
        x=shift_start, line_dash="dot", line_color=TEXT_MUTED,
        annotation_text=f"Shift {shift_start:02d}:00",
        annotation=dict(font=dict(color=TEXT_MUTED, size=10)),
        annotation_position="top",
    )

apply_chart_theme(
    fig,
    title=f"{selected} -- {area} Staffing ({rec_date})",
    height=450,
    xaxis_title="Hour",
    yaxis_title="Lanes",
    yaxis2=dict(
        title="Passengers", overlaying="y", side="right",
        gridcolor=BORDER, linecolor=BORDER, tickfont=dict(color=TEXT_SECONDARY),
        titlefont=dict(color=TEXT_SECONDARY),
    ),
    barmode="group",
    legend=dict(orientation="h", y=-0.15, bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_SECONDARY)),
)
st.plotly_chart(fig, key="staffing_chart", width="stretch")

spacer()

# ---------------------------------------------------------------------------
# Gap Analysis
# ---------------------------------------------------------------------------
gap_hours_list = [h for h in hours_data if not h.get("sla_met")]
if gap_hours_list:
    section_header("SLA Gap Analysis")
    st.markdown(
        f'<p style="color:{TEXT_SECONDARY};font-size:0.9em;margin-bottom:12px;">'
        f'The following hours do NOT meet the SLA target:</p>',
        unsafe_allow_html=True,
    )
    for h in gap_hours_list:
        overshoot = h["expected_wait_min"] - sla_target
        st.markdown(
            f'<div style="background:{SURFACE};border:1px solid {BORDER};'
            f'border-left:4px solid {RED};border-radius:8px;'
            f'padding:10px 16px;margin-bottom:6px;">'
            f'<span style="color:{TEXT_PRIMARY};font-weight:600;">{h["rec_hour"]:02d}:00</span>'
            f'<span style="color:{TEXT_SECONDARY};margin-left:12px;">'
            f'Wait: {h["expected_wait_min"]:.1f} min '
            f'(<span style="color:{RED};">+{overshoot:.1f} over target</span>) | '
            f'{h["forecast_pax"]} pax | '
            f'{h["recommended_lanes"]} lanes</span></div>',
            unsafe_allow_html=True,
        )

spacer()

# ---------------------------------------------------------------------------
# Table + download
# ---------------------------------------------------------------------------
section_header("Hourly Schedule")
show_cols = [
    "rec_hour", "forecast_pax", "recommended_lanes", "recommended_staff",
    "expected_wait_min", "sla_met",
]
show_cols = [c for c in show_cols if c in df.columns]
st.dataframe(df[show_cols], key="staffing_table", width="stretch", hide_index=True)
st.download_button(
    "Download CSV", df[show_cols].to_csv(index=False), "staffing.csv", "text/csv",
    key="staffing_download",
)
