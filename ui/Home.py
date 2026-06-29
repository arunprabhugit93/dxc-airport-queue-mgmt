"""Page 1 -- Operations Command Center."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from api_client import (
    SLA_COLOUR,
    render_alert_banner,
    render_sidebar,
    render_theme_toggle,
    get_airports,
    get_forecast,
    get_queues_current,
    get_recommendations,
    sla_badge_html,
    trend_arrow,
    get_network_health,
    get_shift_handoff,
)
from theme import (
    inject_theme,
    section_header,
    metric_card,
    status_badge,
    priority_badge,
    spacer,
    gauge_figure,
    apply_chart_theme,
    SURFACE,
    BORDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    BLUE_PRIMARY,
    BLUE_LIGHT,
    GREEN,
    YELLOW,
    RED,
    ORANGE,
)

st.set_page_config(page_title="Operations Command Center", layout="wide")
inject_theme()
airport, demo_now = render_sidebar()

# Page header with theme toggle top-right
from theme import t as _t
_p = _t()
_hdr_left, _hdr_right = st.columns([6, 1])
with _hdr_left:
    st.markdown(
        f'<h1 style="color:{_p["text_primary"]};font-weight:700;margin-bottom:4px;">'
        f'Operations Command Center</h1>',
        unsafe_allow_html=True,
    )
with _hdr_right:
    render_theme_toggle()
st.markdown(
    f'<p style="color:{_p["text_secondary"]};font-size:0.95em;margin-bottom:24px;">'
    f'Real-time network overview, SLA compliance, and actionable recommendations</p>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Network health grade
# ---------------------------------------------------------------------------
try:
    nh = get_network_health(demo_now)
    if nh:
        grade_colors = {
            "A": GREEN, "B": BLUE_PRIMARY, "C": YELLOW, "D": ORANGE, "F": RED,
        }
        gc = grade_colors.get(nh["network_grade"], TEXT_MUTED)
        ap_grades = " &nbsp;|&nbsp; ".join(
            f'{a["airport_code"]}: <span style="color:{grade_colors.get(a["grade"], TEXT_MUTED)};'
            f'font-weight:700;">{a["grade"]}</span>'
            for a in nh["airports"]
        )
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:24px;margin-bottom:20px;'
            f'background:{SURFACE};border:1px solid {BORDER};border-radius:8px;padding:20px 24px;">'
            f'<div style="background:{gc};color:#fff;font-size:2.5em;font-weight:900;'
            f'width:80px;height:80px;border-radius:50%;display:flex;align-items:center;'
            f'justify-content:center;flex-shrink:0;">{nh["network_grade"]}</div>'
            f'<div>'
            f'<div style="font-size:1.2em;font-weight:600;color:{TEXT_PRIMARY};">'
            f'Network Health: {nh["network_score"]:.0f}/100</div>'
            f'<div style="font-size:0.85em;color:{TEXT_SECONDARY};margin-top:4px;">{ap_grades}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
except Exception:
    pass

render_alert_banner(demo_now, airport)

# ---------------------------------------------------------------------------
# Fetch core data
# ---------------------------------------------------------------------------
try:
    airports_data = get_airports(demo_now)
    queues_data = get_queues_current(demo_now, airport)
except Exception as e:
    st.error(f"API unavailable: {e}")
    st.stop()

airports = airports_data.get("airports", [])
queues = queues_data.get("queues", [])

# ---------------------------------------------------------------------------
# 1. Critical Alerts Bar
# ---------------------------------------------------------------------------
breach_queues = [q for q in queues if q.get("sla_status") == "BREACH"]
warn_queues = [q for q in queues if q.get("sla_status") == "WARNING"]

if breach_queues:
    breach_msgs = [
        f"{q['airport_code']} {q['area_type']}: {q['wait_min']:.1f} min"
        for q in breach_queues
    ]
    st.markdown(
        f'<div style="background:#F8514915;border:1px solid #F85149;border-left:4px solid {RED};'
        f'border-radius:8px;padding:12px 16px;margin-bottom:8px;">'
        f'<span style="color:{RED};font-weight:700;font-size:0.8em;letter-spacing:0.05em;">'
        f'SLA BREACH</span>'
        f'<span style="color:{TEXT_PRIMARY};margin-left:10px;">{" | ".join(breach_msgs)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

if warn_queues:
    warn_msgs = [
        f"{q['airport_code']} {q['area_type']}: {q['wait_min']:.1f} min"
        for q in warn_queues[:5]
    ]
    st.markdown(
        f'<div style="background:#D2992215;border:1px solid #D29922;border-left:4px solid {YELLOW};'
        f'border-radius:8px;padding:12px 16px;margin-bottom:8px;">'
        f'<span style="color:{YELLOW};font-weight:700;font-size:0.8em;letter-spacing:0.05em;">'
        f'SLA WARNING</span>'
        f'<span style="color:{TEXT_PRIMARY};margin-left:10px;">{" | ".join(warn_msgs)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

spacer()

# ---------------------------------------------------------------------------
# 2. Actionable Recommendations Panel
# ---------------------------------------------------------------------------
rec_airport = airport if airport != "All" else None
recs_data = get_recommendations(demo_now, rec_airport)

if recs_data and recs_data.get("recommendations"):
    section_header("Actionable Recommendations")
    recs = recs_data["recommendations"][:5]
    for rec in recs:
        p = rec.get("priority", "MEDIUM")
        colour = {"HIGH": RED, "MEDIUM": YELLOW, "LOW": GREEN}.get(p.upper(), TEXT_MUTED)
        badge = priority_badge(p)
        st.markdown(
            f'<div style="background:{SURFACE};border:1px solid {BORDER};'
            f'border-left:4px solid {colour};border-radius:8px;padding:16px 20px;margin-bottom:10px;">'
            f'<div style="margin-bottom:6px;">{badge} '
            f'<span style="color:{TEXT_PRIMARY};font-weight:600;margin-left:8px;">'
            f'{rec.get("airport_code", "")} - {rec.get("area", "")}</span></div>'
            f'<div style="color:{TEXT_PRIMARY};font-size:0.95em;">{rec.get("action", "")}</div>'
            f'<div style="color:{TEXT_SECONDARY};font-size:0.85em;margin-top:4px;">'
            f'Reason: {rec.get("reason", "")}</div>'
            f'<div style="color:{BLUE_LIGHT};font-size:0.85em;margin-top:2px;">'
            f'Expected impact: {rec.get("impact", "")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    spacer()

# ---------------------------------------------------------------------------
# 3. Airport Network Status Map
# ---------------------------------------------------------------------------
if airports:
    section_header("Airport Network Status")
    df_map = pd.DataFrame(airports)
    fig_map = px.scatter_geo(
        df_map,
        lat="lat",
        lon="lon",
        color="sla_status",
        size="total_pax_today",
        hover_name="name",
        hover_data={
            "airport_code": True,
            "worst_wait_min": ":.1f",
            "active_anomalies": True,
            "total_pax_today": ":,",
            "sla_status": True,
            "lat": False,
            "lon": False,
        },
        color_discrete_map=SLA_COLOUR,
        scope="usa",
        size_max=35,
    )
    fig_map.update_layout(
        height=500,
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_SECONDARY),
        geo=dict(
            showland=True,
            landcolor="#161B22",
            showlakes=True,
            lakecolor="#0E1117",
            coastlinecolor=BORDER,
            bgcolor="rgba(0,0,0,0)",
            showframe=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.05,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT_SECONDARY),
        ),
    )
    st.plotly_chart(fig_map, key="home_map", use_container_width=False, width="stretch")

    spacer()

# ---------------------------------------------------------------------------
# 4. KPI Gauge Strip
# ---------------------------------------------------------------------------
if airports:
    worst_wait = max(a["worst_wait_min"] for a in airports)
    breach_count = sum(1 for q in queues if q["sla_status"] == "BREACH")
    total_anomalies = sum(a["active_anomalies"] for a in airports)
    total_pax = sum(a["total_pax_today"] for a in airports)

    total_queues = len(queues) if queues else 1
    ok_count = sum(1 for q in queues if q["sla_status"] == "OK")
    sla_compliance = round((ok_count / total_queues) * 100, 1) if total_queues else 100.0

    section_header("Key Performance Indicators")
    g1, g2, g3, g4 = st.columns(4)

    with g1:
        fig_g1 = gauge_figure(
            worst_wait, "Worst Wait (min)",
            max_val=30, good_threshold=7, warn_threshold=10, threshold_val=10,
        )
        st.plotly_chart(fig_g1, key="home_gauge_wait", width="stretch")

    with g2:
        fig_g2 = gauge_figure(
            sla_compliance, "SLA Compliance (%)",
            max_val=100, good_threshold=95, warn_threshold=80,
            suffix="%", threshold_val=95,
        )
        st.plotly_chart(fig_g2, key="home_gauge_sla", width="stretch")

    with g3:
        fig_g3 = go.Figure(go.Indicator(
            mode="number",
            value=total_anomalies,
            title=dict(text="Active Anomalies", font=dict(size=14, color=TEXT_SECONDARY)),
            number=dict(
                font=dict(size=48, color=RED if total_anomalies > 0 else GREEN),
            ),
        ))
        fig_g3.update_layout(
            height=220, margin=dict(l=20, r=20, t=50, b=10),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_g3, key="home_gauge_anom", width="stretch")

    with g4:
        fig_g4 = go.Figure(go.Indicator(
            mode="number",
            value=total_pax,
            title=dict(text="Total Passengers Today", font=dict(size=14, color=TEXT_SECONDARY)),
            number=dict(
                font=dict(size=48, color=BLUE_PRIMARY),
                valueformat=",",
            ),
        ))
        fig_g4.update_layout(
            height=220, margin=dict(l=20, r=20, t=50, b=10),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_g4, key="home_gauge_pax", width="stretch")

    spacer()

# ---------------------------------------------------------------------------
# 5. Live Queue Table
# ---------------------------------------------------------------------------
section_header("Live Queue Status")
if queues:
    rows_html = ""
    for q in queues:
        sla_html = sla_badge_html(q["sla_status"])
        trend_html = trend_arrow(q.get("trend", "FLAT"))
        breach_in = q.get("predicted_breach_in_min")
        breach_text = f"{breach_in} min" if breach_in is not None else "--"
        breach_colour = RED if breach_in is not None and breach_in <= 30 else TEXT_MUTED

        rows_html += (
            f"<tr style='border-bottom:1px solid {BORDER};'>"
            f"<td style='padding:10px 12px;color:{TEXT_PRIMARY};font-weight:600;'>{q['airport_code']}</td>"
            f"<td style='padding:10px 12px;color:{TEXT_SECONDARY};'>{q['area_type']}</td>"
            f"<td style='padding:10px 12px;text-align:center;color:{TEXT_PRIMARY};'>{q['pax_last_hour']}</td>"
            f"<td style='padding:10px 12px;text-align:center;color:{TEXT_PRIMARY};'>{q['lanes_open']}</td>"
            f"<td style='padding:10px 12px;text-align:center;font-weight:700;color:{TEXT_PRIMARY};'>"
            f"{q['wait_min']:.1f}</td>"
            f"<td style='padding:10px 12px;text-align:center;'>{sla_html}</td>"
            f"<td style='padding:10px 12px;text-align:center;'>{trend_html}</td>"
            f"<td style='padding:10px 12px;text-align:center;color:{breach_colour};'>{breach_text}</td>"
            f"</tr>"
        )

    table_html = (
        f"<div style='overflow-x:auto;background:{SURFACE};border:1px solid {BORDER};border-radius:8px;'>"
        f"<table style='width:100%;border-collapse:collapse;'>"
        f"<thead><tr style='border-bottom:2px solid {BORDER};'>"
        f"<th style='text-align:left;padding:12px;color:{TEXT_SECONDARY};font-size:0.8em;"
        f"text-transform:uppercase;letter-spacing:0.05em;'>Airport</th>"
        f"<th style='text-align:left;padding:12px;color:{TEXT_SECONDARY};font-size:0.8em;"
        f"text-transform:uppercase;letter-spacing:0.05em;'>Area</th>"
        f"<th style='text-align:center;padding:12px;color:{TEXT_SECONDARY};font-size:0.8em;"
        f"text-transform:uppercase;letter-spacing:0.05em;'>Pax/hr</th>"
        f"<th style='text-align:center;padding:12px;color:{TEXT_SECONDARY};font-size:0.8em;"
        f"text-transform:uppercase;letter-spacing:0.05em;'>Lanes</th>"
        f"<th style='text-align:center;padding:12px;color:{TEXT_SECONDARY};font-size:0.8em;"
        f"text-transform:uppercase;letter-spacing:0.05em;'>Wait (min)</th>"
        f"<th style='text-align:center;padding:12px;color:{TEXT_SECONDARY};font-size:0.8em;"
        f"text-transform:uppercase;letter-spacing:0.05em;'>SLA</th>"
        f"<th style='text-align:center;padding:12px;color:{TEXT_SECONDARY};font-size:0.8em;"
        f"text-transform:uppercase;letter-spacing:0.05em;'>Trend</th>"
        f"<th style='text-align:center;padding:12px;color:{TEXT_SECONDARY};font-size:0.8em;"
        f"text-transform:uppercase;letter-spacing:0.05em;'>Breach In</th>"
        f"</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        f"</table></div>"
    )
    st.markdown(table_html, unsafe_allow_html=True)
else:
    st.info("No queue data at this time.")

spacer()

# ---------------------------------------------------------------------------
# 6. Next 60-min Forecast Mini-Chart
# ---------------------------------------------------------------------------
section_header("Next 60-Minute Forecast")
forecast_airport = airport if airport != "All" else "ATL"
try:
    fc = get_forecast(demo_now, forecast_airport, horizon=60)
    if fc.get("points"):
        df_fc = pd.DataFrame(fc["points"])
        fig_fc = go.Figure()
        fig_fc.add_trace(go.Scatter(
            x=df_fc["target_ts"],
            y=df_fc["pred_wait_min"],
            mode="lines+markers",
            name="Predicted Wait",
            line=dict(color=BLUE_PRIMARY, width=2.5),
            marker=dict(size=6),
        ))
        if "upper_min" in df_fc.columns and "lower_min" in df_fc.columns:
            fig_fc.add_trace(go.Scatter(
                x=pd.concat([df_fc["target_ts"], df_fc["target_ts"][::-1]]),
                y=pd.concat([df_fc["upper_min"], df_fc["lower_min"][::-1]]),
                fill="toself",
                fillcolor="rgba(0,128,255,0.15)",
                line=dict(color="rgba(255,255,255,0)"),
                name="Confidence Band",
            ))
        fig_fc.add_hline(
            y=10, line_dash="dash", line_color=RED,
            annotation_text="SLA Target (10 min)",
            annotation=dict(font=dict(color=RED)),
        )
        apply_chart_theme(
            fig_fc,
            title=f"{forecast_airport} -- Security Wait Forecast",
            height=320,
            xaxis_title="Time",
            yaxis_title="Wait (min)",
            showlegend=True,
            legend=dict(orientation="h", y=-0.2, bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_SECONDARY)),
        )
        st.plotly_chart(fig_fc, key="home_forecast", width="stretch")
    else:
        st.info("No forecast data available.")
except Exception:
    st.info("Forecast data not available for this time window.")

spacer()

# ---------------------------------------------------------------------------
# 7. Shift Handoff Summary
# ---------------------------------------------------------------------------
section_header("Shift Handoff Summary")
try:
    handoff_ap = forecast_airport if airport != "All" else None
    handoff_data = get_shift_handoff(demo_now, airport=handoff_ap)
    if handoff_data and handoff_data.get("handoffs"):
        for h in handoff_data["handoffs"][:3]:
            sev_color = RED if h["sla_breaches"] > 0 else GREEN
            st.markdown(
                f'<div style="background:{SURFACE};border:1px solid {BORDER};'
                f'border-left:4px solid {sev_color};border-radius:8px;padding:16px 20px;'
                f'margin-bottom:10px;">'
                f'<div style="color:{TEXT_PRIMARY};font-weight:600;">{h["airport_code"]}'
                f'<span style="color:{TEXT_MUTED};font-weight:400;margin-left:12px;font-size:0.85em;">'
                f'{h["shift_start"][:16]} to {h["shift_end"][:16]}</span></div>'
                f'<div style="color:{TEXT_SECONDARY};font-size:0.95em;margin-top:6px;">{h["summary"]}</div>'
                f'<div style="color:{TEXT_MUTED};font-size:0.8em;margin-top:6px;">'
                f'Pax: {h["total_pax"]:,}  |  Anomalies: {h["anomalies_during_shift"]}  |  '
                f'Outlook: {h["next_shift_outlook"]}</div></div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("Shift handoff data not available.")
except Exception:
    pass
