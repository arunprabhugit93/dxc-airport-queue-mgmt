"""Page 4 -- Predictive Intelligence."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api_client import (
    AIRPORT_CODES,
    SLA_COLOUR,
    render_alert_banner,
    render_sidebar,
    get_forecast,
    get_models,
)

st.set_page_config(page_title="Predictive Intelligence", layout="wide", page_icon="✈️")
airport, demo_now = render_sidebar()

st.title("Predictive Intelligence")
st.caption("AI-powered wait-time forecasts with confidence bands and breach warnings")
render_alert_banner(demo_now, airport)

try:
    models_data = get_models()
    models = models_data.get("models", [])
except Exception as e:
    st.error(f"Could not load models: {e}")
    st.stop()

model_names = [m["name"] for m in models]
model_labels = {m["name"]: m["label"] for m in models}
model_horizons = {m["name"]: m.get("horizon_max_min", 180) for m in models}

with st.sidebar:
    st.divider()
    model = st.selectbox(
        "Model", model_names,
        format_func=lambda n: model_labels.get(n, n),
        key="fc_model",
    )
    area = st.selectbox(
        "Checkpoint",
        ["SECURITY_TSA", "SECURITY_PRECHECK"],
        key="fc_area",
    )
    max_h = model_horizons.get(model, 180)
    horizon = st.slider(
        "Horizon (min)", 15, max_h, min(60, max_h), step=15, key="fc_horizon",
    )
    compare_all = st.toggle("Compare all airports", key="fc_compare")
    compare_models = st.toggle("Compare all models", key="fc_compare_models")

selected = airport if airport != "All" else "ATL"

# ---------------------------------------------------------------------------
# Helper: check for predicted breach
# ---------------------------------------------------------------------------


def _breach_callout(points: list[dict]) -> None:
    """Show a prominent callout if SLA breach is predicted."""
    for pt in points:
        if pt.get("pred_wait_min", 0) >= 10:
            horizon_min = pt.get("horizon_min", 0)
            st.error(
                f"SLA BREACH PREDICTED in {horizon_min} minutes -- "
                f"predicted wait {pt['pred_wait_min']:.1f} min. "
                f"Consider opening additional lanes now."
            )
            return
    st.success("No SLA breach predicted within the forecast window.")


# ---------------------------------------------------------------------------
# Multi-model comparison
# ---------------------------------------------------------------------------
if compare_models and not compare_all:
    st.subheader(f"{selected} -- All Models Comparison ({area})")
    fig_mm = go.Figure()
    colours = ["#2980b9", "#e74c3c", "#2ecc71", "#9b59b6", "#f39c12"]

    for idx, m_name in enumerate(model_names):
        try:
            m_horizon = min(horizon, model_horizons.get(m_name, 180))
            fc = get_forecast(demo_now, selected, m_horizon, area, m_name)
            pts = fc.get("points", [])
            if pts:
                df_m = pd.DataFrame(pts)
                colour = colours[idx % len(colours)]
                fig_mm.add_trace(go.Scatter(
                    x=df_m["target_ts"],
                    y=df_m["pred_wait_min"],
                    mode="lines+markers",
                    name=model_labels.get(m_name, m_name),
                    line=dict(color=colour, width=2),
                    marker=dict(size=4),
                ))
        except Exception:
            continue

    fig_mm.add_hline(y=10, line_dash="dash", line_color="#e74c3c", annotation_text="SLA 10 min")
    fig_mm.update_layout(
        title=f"{selected} -- {area}: Model Comparison",
        xaxis_title="Time",
        yaxis_title="Wait (min)",
        height=500,
        legend=dict(orientation="h", y=-0.15),
    )
    st.plotly_chart(fig_mm, width="stretch")

# ---------------------------------------------------------------------------
# Single airport view
# ---------------------------------------------------------------------------
elif not compare_all:
    try:
        fc = get_forecast(demo_now, selected, horizon, area, model)
        points = fc.get("points", [])
    except Exception as e:
        st.error(f"Forecast failed: {e}")
        st.stop()

    if not points:
        st.info("No forecast data for this selection.")
        st.stop()

    # Breach callout
    _breach_callout(points)

    df = pd.DataFrame(points)

    # Main forecast chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["target_ts"], y=df["pred_wait_min"],
        mode="lines+markers", name="Predicted Wait",
        line=dict(color="#2980b9", width=2),
        marker=dict(size=5),
    ))
    if "lower_min" in df.columns and "upper_min" in df.columns:
        fig.add_trace(go.Scatter(
            x=pd.concat([df["target_ts"], df["target_ts"][::-1]]),
            y=pd.concat([df["upper_min"], df["lower_min"][::-1]]),
            fill="toself", fillcolor="rgba(41,128,185,0.12)",
            line=dict(color="rgba(255,255,255,0)"), name="Confidence Band",
        ))
    fig.add_hline(y=10, line_dash="dash", line_color="#e74c3c", annotation_text="SLA 10 min")
    fig.update_layout(
        title=f"{selected} {area} -- {model_labels.get(model, model)}",
        xaxis_title="Time", yaxis_title="Wait (min)", height=450,
        legend=dict(orientation="h", y=-0.15),
    )
    st.plotly_chart(fig, width="stretch")

    # Throughput forecast
    if "pred_throughput" in df.columns and df["pred_throughput"].notna().any():
        st.subheader("Throughput Forecast")
        fig_tp = go.Figure(go.Bar(
            x=df["target_ts"],
            y=df["pred_throughput"],
            marker_color="#3498db",
            text=df["pred_throughput"],
            textposition="auto",
        ))
        fig_tp.update_layout(
            height=280, xaxis_title="Time", yaxis_title="Passengers",
            title="Predicted Throughput",
        )
        st.plotly_chart(fig_tp, width="stretch")

    # Data table + download
    st.subheader("Forecast Data")
    st.dataframe(df, width="stretch", hide_index=True)
    st.download_button(
        "Download CSV", df.to_csv(index=False), "forecast.csv", "text/csv",
    )

# ---------------------------------------------------------------------------
# Multi-airport comparison
# ---------------------------------------------------------------------------
else:
    st.subheader(f"All Airports -- {area} ({model_labels.get(model, model)})")
    fig = go.Figure()
    colours = ["#2980b9", "#e74c3c", "#2ecc71", "#9b59b6", "#f39c12"]
    for idx, code in enumerate(AIRPORT_CODES):
        try:
            fc = get_forecast(demo_now, code, horizon, area, model)
            pts = fc.get("points", [])
            if pts:
                df_a = pd.DataFrame(pts)
                fig.add_trace(go.Scatter(
                    x=df_a["target_ts"], y=df_a["pred_wait_min"],
                    mode="lines+markers", name=code,
                    line=dict(color=colours[idx % len(colours)], width=2),
                ))
        except Exception:
            continue
    fig.add_hline(y=10, line_dash="dash", line_color="#e74c3c", annotation_text="SLA 10 min")
    fig.update_layout(
        title=f"All Airports -- {area} -- {model_labels.get(model, model)}",
        xaxis_title="Time", yaxis_title="Wait (min)", height=500,
        legend=dict(orientation="h", y=-0.15),
    )
    st.plotly_chart(fig, width="stretch")
