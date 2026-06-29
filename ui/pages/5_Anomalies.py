"""Page 5 -- Anomaly & Incident Intelligence."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api_client import (
    SEVERITY_COLOUR,
    render_alert_banner,
    render_sidebar,
    get_anomalies,
    severity_badge_html,
)
from theme import (
    inject_theme,
    section_header,
    metric_card,
    severity_badge,
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
    ORANGE,
)

st.set_page_config(page_title="Anomaly Intelligence", layout="wide")
inject_theme()
airport, demo_now = render_sidebar()

# Page header
st.markdown(
    '<h1 style="color:#FAFAFA;font-weight:700;margin-bottom:4px;">Anomaly Intelligence</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="color:#8B949E;font-size:0.95em;margin-bottom:24px;">'
    'Real-time detection and analysis of operational anomalies</p>',
    unsafe_allow_html=True,
)
render_alert_banner(demo_now, airport)

with st.sidebar:
    st.divider()
    hours = st.slider("Lookback window (hours)", 1, 720, 24, key="anom_hours")
    type_filter = st.multiselect(
        "Anomaly types", ["SPIKE", "DROP", "CROSS_AIRPORT", "SEASONAL"],
        default=["SPIKE", "DROP", "CROSS_AIRPORT", "SEASONAL"], key="anom_types",
    )
    severity_filter = st.multiselect(
        "Severity", ["LOW", "MEDIUM", "HIGH"], default=["LOW", "MEDIUM", "HIGH"], key="anom_sev",
    )

ap = airport if airport != "All" else None
try:
    data = get_anomalies(demo_now, airport=ap, hours=hours)
except Exception as e:
    st.error(f"API error: {e}")
    st.stop()

events = data.get("events", [])
if not events:
    st.info("No anomalies detected in this window.")
    st.stop()

df = pd.DataFrame(events)
df = df[df["anomaly_type"].isin(type_filter) & df["severity"].isin(severity_filter)]

if df.empty:
    st.info("No anomalies match the current filters.")
    st.stop()

# ---------------------------------------------------------------------------
# 1. Active HIGH-Severity Incidents
# ---------------------------------------------------------------------------
high_events = df[df["severity"] == "HIGH"]

if not high_events.empty:
    section_header(f"Active HIGH-Severity Incidents ({len(high_events)})")
    incident_cols = st.columns(min(len(high_events), 3))
    for idx, (_, evt) in enumerate(high_events.head(6).iterrows()):
        col = incident_cols[idx % len(incident_cols)]
        with col:
            st.markdown(
                f'<div style="background:{SURFACE};border:1px solid {RED};'
                f'border-left:4px solid {RED};border-radius:8px;'
                f'padding:16px 20px;margin-bottom:10px;">'
                f'<div style="font-weight:700;color:{RED};font-size:0.95em;">'
                f'{evt["airport_code"]} -- {evt.get("area_type", "N/A")}</div>'
                f'<div style="margin:8px 0;font-size:0.9em;color:{TEXT_PRIMARY};">'
                f'{evt.get("description", "High-severity anomaly detected")}</div>'
                f'<div style="font-size:0.8em;color:{TEXT_MUTED};">'
                f'{evt["anomaly_type"]} | {evt["detector"]}</div>'
                f'<div style="font-size:0.8em;color:{TEXT_MUTED};margin-top:4px;">'
                f'Detected: {evt["detected_at"]}</div>'
                f'<div style="margin-top:6px;font-size:0.8em;color:{TEXT_SECONDARY};">'
                f'Observed: <span style="color:{TEXT_PRIMARY};font-weight:600;">'
                f'{evt["observed_value"]:.1f}</span>'
                f'{" vs expected " + str(round(evt["expected_value"], 1)) if evt.get("expected_value") else ""}'
                f' (score: {evt["score"]:.2f})</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    spacer()

# ---------------------------------------------------------------------------
# 2. Impact Assessment Summary
# ---------------------------------------------------------------------------
total_events = len(df)
high_count = len(high_events)
medium_count = len(df[df["severity"] == "MEDIUM"])
airports_affected = df["airport_code"].nunique()

section_header("Impact Assessment")

sm1, sm2, sm3, sm4 = st.columns(4)
with sm1:
    st.markdown(metric_card("Total Anomalies", str(total_events)), unsafe_allow_html=True)
with sm2:
    st.markdown(metric_card("HIGH Severity", str(high_count), border_color=RED), unsafe_allow_html=True)
with sm3:
    st.markdown(metric_card("MEDIUM Severity", str(medium_count), border_color=YELLOW), unsafe_allow_html=True)
with sm4:
    st.markdown(metric_card("Airports Affected", str(airports_affected)), unsafe_allow_html=True)

spacer(12)

if high_count > 0:
    st.markdown(
        f'<div style="background:#D2992215;border:1px solid {YELLOW};border-left:4px solid {YELLOW};'
        f'border-radius:8px;padding:12px 16px;">'
        f'<span style="color:{YELLOW};font-weight:700;font-size:0.8em;letter-spacing:0.05em;">'
        f'ATTENTION</span>'
        f'<span style="color:{TEXT_PRIMARY};margin-left:10px;">'
        f'There are {high_count} high-severity incidents across '
        f'{airports_affected} airport(s). These anomalies may indicate '
        f'significant operational disruptions requiring immediate attention.</span></div>',
        unsafe_allow_html=True,
    )

spacer()

# ---------------------------------------------------------------------------
# 3. Timeline Scatter
# ---------------------------------------------------------------------------
section_header("Anomaly Timeline")

fig_tl = go.Figure()
for sev in ["HIGH", "MEDIUM", "LOW"]:
    df_sev = df[df["severity"] == sev]
    if not df_sev.empty:
        fig_tl.add_trace(go.Scatter(
            x=df_sev["detected_at"],
            y=df_sev["airport_code"],
            mode="markers",
            name=sev,
            marker=dict(
                size=df_sev["score"] * 12 + 6,
                color=SEVERITY_COLOUR.get(sev, TEXT_MUTED),
                line=dict(width=1, color=BORDER),
            ),
            text=df_sev["description"],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "%{x}<br>"
                "%{text}<br>"
                "Score: %{marker.size:.0f}<extra></extra>"
            ),
        ))

apply_chart_theme(
    fig_tl,
    height=380,
    xaxis_title="Time",
    yaxis_title="Airport",
    legend=dict(orientation="h", y=-0.15, bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_SECONDARY)),
)
st.plotly_chart(fig_tl, key="anom_timeline", width="stretch")

spacer()

# ---------------------------------------------------------------------------
# 4. Breakdowns
# ---------------------------------------------------------------------------
section_header("Anomaly Breakdown")
col1, col2 = st.columns(2)

with col1:
    type_counts = df["anomaly_type"].value_counts().reset_index()
    type_counts.columns = ["type", "count"]
    type_colors = [BLUE_PRIMARY, RED, YELLOW, GREEN][:len(type_counts)]
    fig_type = go.Figure(go.Bar(
        x=type_counts["type"],
        y=type_counts["count"],
        marker=dict(color=type_colors, opacity=0.9, line=dict(color=BORDER, width=1)),
        text=type_counts["count"],
        textposition="auto",
        textfont=dict(color=TEXT_PRIMARY),
    ))
    apply_chart_theme(
        fig_type,
        title="By Type",
        height=300,
        xaxis_title="Type",
        yaxis_title="Count",
    )
    st.plotly_chart(fig_type, key="anom_by_type", width="stretch")

with col2:
    det_counts = df["detector"].value_counts().reset_index()
    det_counts.columns = ["detector", "count"]
    det_colors = ["#9b59b6", "#1abc9c", ORANGE, "#34495e"][:len(det_counts)]
    fig_det = go.Figure(go.Bar(
        x=det_counts["detector"],
        y=det_counts["count"],
        marker=dict(color=det_colors, opacity=0.9, line=dict(color=BORDER, width=1)),
        text=det_counts["count"],
        textposition="auto",
        textfont=dict(color=TEXT_PRIMARY),
    ))
    apply_chart_theme(
        fig_det,
        title="By Detector",
        height=300,
        xaxis_title="Detector",
        yaxis_title="Count",
    )
    st.plotly_chart(fig_det, key="anom_by_detector", width="stretch")

spacer()

# ---------------------------------------------------------------------------
# 5. Cross-Airport Distribution
# ---------------------------------------------------------------------------
section_header("Cross-Airport Anomaly Distribution")
airport_counts = df["airport_code"].value_counts().reset_index()
airport_counts.columns = ["airport", "count"]

if airports_affected > 1:
    max_share = airport_counts["count"].max() / total_events
    if max_share < 0.5:
        msg = ("Anomalies are distributed across multiple airports -- "
               "this may indicate a systemic issue (weather, system-wide surge, etc.).")
    else:
        top_airport = airport_counts.iloc[0]["airport"]
        msg = (f"Anomalies are concentrated at {top_airport} -- "
               f"likely a localised issue at that airport.")
    st.markdown(
        f'<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;'
        f'padding:12px 16px;margin-bottom:12px;">'
        f'<span style="color:{TEXT_SECONDARY};font-size:0.9em;">{msg}</span></div>',
        unsafe_allow_html=True,
    )

fig_ap = go.Figure(go.Bar(
    x=airport_counts["airport"],
    y=airport_counts["count"],
    marker=dict(color=BLUE_PRIMARY, opacity=0.9, line=dict(color=BORDER, width=1)),
    text=airport_counts["count"],
    textposition="auto",
    textfont=dict(color=TEXT_PRIMARY),
))
apply_chart_theme(
    fig_ap,
    title="Anomalies per Airport",
    height=300,
    xaxis_title="Airport",
    yaxis_title="Count",
)
st.plotly_chart(fig_ap, key="anom_by_airport", width="stretch")

spacer()

# ---------------------------------------------------------------------------
# 6. Event Detail Table
# ---------------------------------------------------------------------------
section_header("Event Details")
display_cols = [
    "detected_at", "airport_code", "area_type", "anomaly_type", "detector",
    "observed_value", "expected_value", "score", "severity", "description",
]
show_cols = [c for c in display_cols if c in df.columns]
st.dataframe(df[show_cols], key="anom_detail_table", width="stretch", hide_index=True)
