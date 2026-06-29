"""Page 5 -- Anomaly & Incident Intelligence."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from api_client import (
    SEVERITY_COLOUR,
    SLA_COLOUR,
    render_alert_banner,
    render_sidebar,
    get_anomalies,
    severity_badge_html,
)

st.set_page_config(page_title="Anomaly & Incident Intelligence", layout="wide", page_icon="✈️")
airport, demo_now = render_sidebar()

st.title("Anomaly & Incident Intelligence")
st.caption("Real-time detection and analysis of operational anomalies")
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
# 1. Active Incidents Panel -- HIGH severity cards
# ---------------------------------------------------------------------------
high_events = df[df["severity"] == "HIGH"]

if not high_events.empty:
    st.subheader(f"Active HIGH-Severity Incidents ({len(high_events)})")
    incident_cols = st.columns(min(len(high_events), 3))
    for idx, (_, evt) in enumerate(high_events.head(6).iterrows()):
        col = incident_cols[idx % len(incident_cols)]
        with col:
            st.markdown(
                f'<div style="border:2px solid #e74c3c;border-radius:8px;'
                f'padding:14px;margin-bottom:10px;background:#e74c3c0a;">'
                f'<div style="font-weight:700;color:#e74c3c;">'
                f'{evt["airport_code"]} -- {evt.get("area_type", "N/A")}</div>'
                f'<div style="margin:6px 0;font-size:0.95em;">'
                f'{evt.get("description", "High-severity anomaly detected")}</div>'
                f'<div style="font-size:0.85em;color:#666;">'
                f'{evt["anomaly_type"]} | {evt["detector"]}</div>'
                f'<div style="font-size:0.85em;color:#888;margin-top:4px;">'
                f'Detected: {evt["detected_at"]}</div>'
                f'<div style="margin-top:6px;font-size:0.85em;">'
                f'Observed: <strong>{evt["observed_value"]:.1f}</strong>'
                f'{" vs expected " + str(round(evt["expected_value"], 1)) if evt.get("expected_value") else ""}'
                f' (score: {evt["score"]:.2f})</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    st.divider()

# ---------------------------------------------------------------------------
# 2. Impact Assessment Summary
# ---------------------------------------------------------------------------
total_events = len(df)
high_count = len(high_events)
medium_count = len(df[df["severity"] == "MEDIUM"])
airports_affected = df["airport_code"].nunique()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Anomalies", total_events)
c2.metric("HIGH Severity", high_count)
c3.metric("MEDIUM Severity", medium_count)
c4.metric("Airports Affected", airports_affected)

# Impact narrative
if high_count > 0:
    st.warning(
        f"There are {high_count} high-severity incidents across "
        f"{airports_affected} airport(s). These anomalies may indicate "
        f"significant operational disruptions requiring immediate attention."
    )

# ---------------------------------------------------------------------------
# 3. Timeline Scatter (enhanced)
# ---------------------------------------------------------------------------
st.subheader("Anomaly Timeline")

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
                color=SEVERITY_COLOUR.get(sev, "#95a5a6"),
                line=dict(width=1, color="#fff"),
            ),
            text=df_sev["description"],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "%{x}<br>"
                "%{text}<br>"
                "Score: %{marker.size:.0f}<extra></extra>"
            ),
        ))

fig_tl.update_layout(
    height=380,
    xaxis_title="Time",
    yaxis_title="Airport",
    legend=dict(orientation="h", y=-0.15),
    margin=dict(l=10, r=10, t=10, b=10),
)
st.plotly_chart(fig_tl, width="stretch")

# ---------------------------------------------------------------------------
# 4. Breakdowns
# ---------------------------------------------------------------------------
st.subheader("Anomaly Breakdown")
col1, col2 = st.columns(2)

with col1:
    type_counts = df["anomaly_type"].value_counts().reset_index()
    type_counts.columns = ["type", "count"]
    fig_type = go.Figure(go.Bar(
        x=type_counts["type"],
        y=type_counts["count"],
        marker_color=["#3498db", "#e74c3c", "#f39c12", "#2ecc71"][:len(type_counts)],
        text=type_counts["count"],
        textposition="auto",
    ))
    fig_type.update_layout(
        title="By Type", height=300,
        xaxis_title="Type", yaxis_title="Count",
    )
    st.plotly_chart(fig_type, width="stretch")

with col2:
    det_counts = df["detector"].value_counts().reset_index()
    det_counts.columns = ["detector", "count"]
    fig_det = go.Figure(go.Bar(
        x=det_counts["detector"],
        y=det_counts["count"],
        marker_color=["#9b59b6", "#1abc9c", "#e67e22", "#34495e"][:len(det_counts)],
        text=det_counts["count"],
        textposition="auto",
    ))
    fig_det.update_layout(
        title="By Detector", height=300,
        xaxis_title="Detector", yaxis_title="Count",
    )
    st.plotly_chart(fig_det, width="stretch")

# ---------------------------------------------------------------------------
# 5. Cross-Airport Correlation
# ---------------------------------------------------------------------------
st.subheader("Cross-Airport Anomaly Distribution")
airport_counts = df["airport_code"].value_counts().reset_index()
airport_counts.columns = ["airport", "count"]

# Determine if anomalies are systemic or localised
if airports_affected > 1:
    max_share = airport_counts["count"].max() / total_events
    if max_share < 0.5:
        st.info(
            "Anomalies are distributed across multiple airports -- "
            "this may indicate a systemic issue (weather, system-wide surge, etc.)."
        )
    else:
        top_airport = airport_counts.iloc[0]["airport"]
        st.info(
            f"Anomalies are concentrated at {top_airport} -- "
            f"likely a localised issue at that airport."
        )

fig_ap = go.Figure(go.Bar(
    x=airport_counts["airport"],
    y=airport_counts["count"],
    marker_color="#2980b9",
    text=airport_counts["count"],
    textposition="auto",
))
fig_ap.update_layout(
    title="Anomalies per Airport", height=300,
    xaxis_title="Airport", yaxis_title="Count",
)
st.plotly_chart(fig_ap, width="stretch")

# ---------------------------------------------------------------------------
# 6. Event Detail Table
# ---------------------------------------------------------------------------
st.subheader("Event Details")
display_cols = [
    "detected_at", "airport_code", "area_type", "anomaly_type", "detector",
    "observed_value", "expected_value", "score", "severity", "description",
]
show_cols = [c for c in display_cols if c in df.columns]
st.dataframe(df[show_cols], width="stretch", hide_index=True)
