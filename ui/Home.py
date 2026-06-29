"""Page 1 -- Airport Operations Command Center."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from api_client import (
    SLA_COLOUR,
    render_alert_banner,
    render_sidebar,
    get_airports,
    get_forecast,
    get_queues_current,
    get_recommendations,
    sla_badge_html,
    trend_arrow,
)

st.set_page_config(page_title="Operations Command Center", layout="wide", page_icon="✈️")
airport, demo_now = render_sidebar()

st.title("Airport Operations Command Center")

# Network health grade
try:
    from api_client import get_network_health
    nh = get_network_health(demo_now)
    if nh:
        grade_colors = {"A": "#2ecc71", "B": "#3498db", "C": "#f39c12", "D": "#e67e22", "F": "#e74c3c"}
        gc = grade_colors.get(nh["network_grade"], "#95a5a6")
        ap_grades = " | ".join(
            f'{a["airport_code"]}: <span style="color:{grade_colors.get(a["grade"],"#aaa")};'
            f'font-weight:700;">{a["grade"]}</span>'
            for a in nh["airports"]
        )
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:20px;margin-bottom:16px;">'
            f'<div style="background:{gc};color:#fff;font-size:2.5em;font-weight:900;'
            f'width:80px;height:80px;border-radius:50%;display:flex;align-items:center;'
            f'justify-content:center;">{nh["network_grade"]}</div>'
            f'<div><div style="font-size:1.2em;font-weight:600;">Network Health: '
            f'{nh["network_score"]:.0f}/100</div>'
            f'<div style="font-size:0.9em;color:#aaa;">{ap_grades}</div></div></div>',
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
# 1. Critical Alerts Bar -- breaches & anomalies
# ---------------------------------------------------------------------------
breach_queues = [q for q in queues if q.get("sla_status") == "BREACH"]
warn_queues = [q for q in queues if q.get("sla_status") == "WARNING"]

if breach_queues:
    breach_msgs = [
        f"{q['airport_code']} {q['area_type']}: {q['wait_min']:.1f} min wait"
        for q in breach_queues
    ]
    st.error("SLA BREACH -- " + " | ".join(breach_msgs))

if warn_queues:
    warn_msgs = [
        f"{q['airport_code']} {q['area_type']}: {q['wait_min']:.1f} min"
        for q in warn_queues[:5]
    ]
    st.warning("SLA WARNING -- " + " | ".join(warn_msgs))

# ---------------------------------------------------------------------------
# 2. Actionable Recommendations Panel
# ---------------------------------------------------------------------------
rec_airport = airport if airport != "All" else None
recs_data = get_recommendations(demo_now, rec_airport)

if recs_data and recs_data.get("recommendations"):
    st.subheader("Actionable Recommendations")
    recs = recs_data["recommendations"][:5]
    for rec in recs:
        priority = rec.get("priority", "MEDIUM")
        colour = {"HIGH": "#e74c3c", "MEDIUM": "#f39c12", "LOW": "#2ecc71"}.get(
            priority.upper(), "#95a5a6"
        )
        border_style = f"border-left: 5px solid {colour}; padding: 12px 16px; margin-bottom: 8px; background: rgba(0,0,0,0.02); border-radius: 4px;"
        st.markdown(
            f'<div style="{border_style}">'
            f'<strong style="color:{colour};">[{priority}]</strong> '
            f'<strong>{rec.get("airport_code", "")} - {rec.get("area", "")}</strong><br/>'
            f'{rec.get("action", "")}<br/>'
            f'<em style="color:#666;">Reason: {rec.get("reason", "")}</em><br/>'
            f'<span style="color:#2980b9;">Expected impact: {rec.get("impact", "")}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# 3. Airport Overview Map
# ---------------------------------------------------------------------------
if airports:
    st.subheader("Airport Network Status")
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
        geo=dict(
            showland=True,
            landcolor="#f0f0f0",
            showlakes=True,
            lakecolor="#e8f4fd",
            coastlinecolor="#ccc",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.05,
            xanchor="center",
            x=0.5,
        ),
    )
    st.plotly_chart(fig_map, width="stretch")

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

    st.subheader("Key Performance Indicators")
    g1, g2, g3, g4 = st.columns(4)

    with g1:
        fig_g1 = go.Figure(go.Indicator(
            mode="gauge+number",
            value=worst_wait,
            title={"text": "Worst Wait (min)"},
            gauge={
                "axis": {"range": [0, 30]},
                "bar": {"color": "#2c3e50"},
                "steps": [
                    {"range": [0, 7], "color": "#2ecc71"},
                    {"range": [7, 10], "color": "#f39c12"},
                    {"range": [10, 30], "color": "#e74c3c"},
                ],
                "threshold": {
                    "line": {"color": "#e74c3c", "width": 3},
                    "thickness": 0.8,
                    "value": 10,
                },
            },
        ))
        fig_g1.update_layout(height=220, margin=dict(l=20, r=20, t=50, b=10))
        st.plotly_chart(fig_g1, width="stretch")

    with g2:
        fig_g2 = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=sla_compliance,
            title={"text": "SLA Compliance (%)"},
            delta={"reference": 95, "increasing": {"color": "#2ecc71"}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#2c3e50"},
                "steps": [
                    {"range": [0, 80], "color": "#e74c3c"},
                    {"range": [80, 95], "color": "#f39c12"},
                    {"range": [95, 100], "color": "#2ecc71"},
                ],
                "threshold": {
                    "line": {"color": "#2ecc71", "width": 3},
                    "thickness": 0.8,
                    "value": 95,
                },
            },
        ))
        fig_g2.update_layout(height=220, margin=dict(l=20, r=20, t=50, b=10))
        st.plotly_chart(fig_g2, width="stretch")

    with g3:
        fig_g3 = go.Figure(go.Indicator(
            mode="number+delta",
            value=total_anomalies,
            title={"text": "Active Anomalies"},
            delta={"reference": 0, "increasing": {"color": "#e74c3c"}},
            number={"font": {"size": 54, "color": "#e74c3c" if total_anomalies > 0 else "#2ecc71"}},
        ))
        fig_g3.update_layout(height=220, margin=dict(l=20, r=20, t=50, b=10))
        st.plotly_chart(fig_g3, width="stretch")

    with g4:
        fig_g4 = go.Figure(go.Indicator(
            mode="number",
            value=total_pax,
            title={"text": "Total Passengers Today"},
            number={"font": {"size": 54, "color": "#2980b9"}, "valueformat": ","},
        ))
        fig_g4.update_layout(height=220, margin=dict(l=20, r=20, t=50, b=10))
        st.plotly_chart(fig_g4, width="stretch")

# ---------------------------------------------------------------------------
# 5. Live Queue Table (enhanced)
# ---------------------------------------------------------------------------
st.subheader("Live Queue Status")
if queues:
    rows_html = ""
    for q in queues:
        sla_html = sla_badge_html(q["sla_status"])
        trend_html = trend_arrow(q.get("trend", "FLAT"))
        breach_in = q.get("predicted_breach_in_min")
        breach_text = f"{breach_in} min" if breach_in is not None else "--"
        breach_colour = "#e74c3c" if breach_in is not None and breach_in <= 30 else "#666"

        rows_html += (
            f"<tr>"
            f"<td><strong>{q['airport_code']}</strong></td>"
            f"<td>{q['area_type']}</td>"
            f"<td style='text-align:center;'>{q['pax_last_hour']}</td>"
            f"<td style='text-align:center;'>{q['lanes_open']}</td>"
            f"<td style='text-align:center;font-weight:600;'>{q['wait_min']:.1f}</td>"
            f"<td style='text-align:center;'>{sla_html}</td>"
            f"<td style='text-align:center;'>{trend_html}</td>"
            f"<td style='text-align:center;color:{breach_colour};'>{breach_text}</td>"
            f"</tr>"
        )

    table_html = (
        "<div style='overflow-x:auto;'>"
        "<table style='width:100%;border-collapse:collapse;'>"
        "<thead><tr style='border-bottom:2px solid #ddd;'>"
        "<th style='text-align:left;padding:8px;'>Airport</th>"
        "<th style='text-align:left;padding:8px;'>Area</th>"
        "<th style='text-align:center;padding:8px;'>Pax/hr</th>"
        "<th style='text-align:center;padding:8px;'>Lanes</th>"
        "<th style='text-align:center;padding:8px;'>Wait (min)</th>"
        "<th style='text-align:center;padding:8px;'>SLA</th>"
        "<th style='text-align:center;padding:8px;'>Trend</th>"
        "<th style='text-align:center;padding:8px;'>Breach In</th>"
        "</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table></div>"
    )
    st.markdown(table_html, unsafe_allow_html=True)
else:
    st.info("No queue data at this time.")

# ---------------------------------------------------------------------------
# 6. Next 60-min Forecast Mini-Chart
# ---------------------------------------------------------------------------
st.subheader("Next 60-Minute Forecast")
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
            line=dict(color="#2980b9", width=2),
            marker=dict(size=5),
        ))
        if "upper_min" in df_fc.columns and "lower_min" in df_fc.columns:
            fig_fc.add_trace(go.Scatter(
                x=pd.concat([df_fc["target_ts"], df_fc["target_ts"][::-1]]),
                y=pd.concat([df_fc["upper_min"], df_fc["lower_min"][::-1]]),
                fill="toself",
                fillcolor="rgba(41,128,185,0.12)",
                line=dict(color="rgba(255,255,255,0)"),
                name="Confidence Band",
            ))
        fig_fc.add_hline(
            y=10, line_dash="dash", line_color="#e74c3c",
            annotation_text="SLA Target (10 min)",
        )
        fig_fc.update_layout(
            title=f"{forecast_airport} -- Security Wait Forecast",
            height=320,
            xaxis_title="Time",
            yaxis_title="Wait (min)",
            showlegend=True,
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig_fc, width="stretch")
    else:
        st.info("No forecast data available.")
except Exception:
    st.info("Forecast data not available for this time window.")

# ---------------------------------------------------------------------------
# Shift Handoff Summary
# ---------------------------------------------------------------------------
st.subheader("Shift Handoff Summary")
try:
    from api_client import get_shift_handoff
    handoff_ap = forecast_airport if airport != "All" else None
    handoff_data = get_shift_handoff(demo_now, airport=handoff_ap)
    if handoff_data and handoff_data.get("handoffs"):
        for h in handoff_data["handoffs"][:3]:
            sev_color = "#e74c3c" if h["sla_breaches"] > 0 else "#2ecc71"
            st.markdown(
                f'<div style="border-left:4px solid {sev_color};padding:12px 16px;'
                f'margin-bottom:10px;border-radius:4px;background:rgba(255,255,255,0.03);">'
                f'<strong>{h["airport_code"]}</strong> | '
                f'{h["shift_start"][:16]} to {h["shift_end"][:16]}<br/>'
                f'{h["summary"]}<br/>'
                f'<span style="color:#888;font-size:0.9em;">'
                f'Pax: {h["total_pax"]:,} | Anomalies: {h["anomalies_during_shift"]} | '
                f'Outlook: {h["next_shift_outlook"]}</span></div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("Shift handoff data not available.")
except Exception:
    pass
