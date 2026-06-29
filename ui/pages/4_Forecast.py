"""Page 4 -- Predictive Intelligence."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api_client import (
    AIRPORT_CODES,
    render_alert_banner,
    render_sidebar,
    get_forecast,
    get_models,
)
from theme import (
    inject_theme,
    section_header,
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

st.set_page_config(page_title="Predictive Intelligence", layout="wide")
inject_theme()
airport, demo_now = render_sidebar()

# Page header
st.markdown(
    '<h1 style="color:#FAFAFA;font-weight:700;margin-bottom:4px;">Predictive Intelligence</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="color:#8B949E;font-size:0.95em;margin-bottom:24px;">'
    'AI-powered wait-time forecasts with confidence bands and breach warnings</p>',
    unsafe_allow_html=True,
)
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

FORECAST_COLOR = BLUE_PRIMARY
FORECAST_DASH_COLOR = "#FF9500"


# ---------------------------------------------------------------------------
# Breach callout
# ---------------------------------------------------------------------------
def _breach_callout(points: list[dict]) -> None:
    for pt in points:
        if pt.get("pred_wait_min", 0) >= 10:
            horizon_min = pt.get("horizon_min", 0)
            st.markdown(
                f'<div style="background:#F8514915;border:1px solid {RED};border-left:4px solid {RED};'
                f'border-radius:8px;padding:14px 18px;margin-bottom:12px;">'
                f'<span style="color:{RED};font-weight:700;font-size:0.8em;letter-spacing:0.05em;">'
                f'BREACH PREDICTED</span>'
                f'<span style="color:{TEXT_PRIMARY};margin-left:10px;">'
                f'In {horizon_min} minutes -- predicted wait {pt["pred_wait_min"]:.1f} min. '
                f'Consider opening additional lanes now.</span></div>',
                unsafe_allow_html=True,
            )
            return
    st.markdown(
        f'<div style="background:#2EA04315;border:1px solid {GREEN};border-left:4px solid {GREEN};'
        f'border-radius:8px;padding:14px 18px;margin-bottom:12px;">'
        f'<span style="color:{GREEN};font-weight:700;font-size:0.8em;letter-spacing:0.05em;">'
        f'ALL CLEAR</span>'
        f'<span style="color:{TEXT_PRIMARY};margin-left:10px;">'
        f'No SLA breach predicted within the forecast window.</span></div>',
        unsafe_allow_html=True,
    )


def _apply_dark_chart(fig: go.Figure, title: str, height: int = 450) -> None:
    """Apply consistent dark theme to a forecast chart."""
    apply_chart_theme(
        fig,
        title=title,
        height=height,
        xaxis_title="Time",
        yaxis_title="Wait (min)",
        showlegend=True,
        legend=dict(orientation="h", y=-0.15, bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_SECONDARY)),
    )


# ---------------------------------------------------------------------------
# Multi-model comparison
# ---------------------------------------------------------------------------
if compare_models and not compare_all:
    section_header(f"{selected} -- All Models Comparison ({area})")
    fig_mm = go.Figure()
    line_styles = ["solid", "dash", "dot", "dashdot", "longdash"]
    colours = [BLUE_PRIMARY, RED, GREEN, "#9b59b6", ORANGE]

    for idx, m_name in enumerate(model_names):
        try:
            m_horizon = min(horizon, model_horizons.get(m_name, 180))
            fc = get_forecast(demo_now, selected, m_horizon, area, m_name)
            pts = fc.get("points", [])
            if pts:
                df_m = pd.DataFrame(pts)
                fig_mm.add_trace(go.Scatter(
                    x=df_m["target_ts"],
                    y=df_m["pred_wait_min"],
                    mode="lines+markers",
                    name=model_labels.get(m_name, m_name),
                    line=dict(color=colours[idx % len(colours)], width=2.5,
                              dash=line_styles[idx % len(line_styles)]),
                    marker=dict(size=5),
                ))
        except Exception:
            continue

    fig_mm.add_hline(y=10, line_dash="dash", line_color=RED, annotation_text="SLA 10 min",
                     annotation=dict(font=dict(color=RED)))
    _apply_dark_chart(fig_mm, f"{selected} -- {area}: Model Comparison", 500)
    st.plotly_chart(fig_mm, key="fc_multi_model", width="stretch")

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

    _breach_callout(points)
    spacer()

    df = pd.DataFrame(points)

    # Main forecast chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["target_ts"], y=df["pred_wait_min"],
        mode="lines+markers", name="Predicted Wait",
        line=dict(color=FORECAST_COLOR, width=2.5),
        marker=dict(size=6),
    ))
    if "lower_min" in df.columns and "upper_min" in df.columns:
        fig.add_trace(go.Scatter(
            x=pd.concat([df["target_ts"], df["target_ts"][::-1]]),
            y=pd.concat([df["upper_min"], df["lower_min"][::-1]]),
            fill="toself", fillcolor="rgba(0,128,255,0.15)",
            line=dict(color="rgba(255,255,255,0)"), name="Confidence Band",
        ))
    fig.add_hline(y=10, line_dash="dash", line_color=RED, annotation_text="SLA 10 min",
                  annotation=dict(font=dict(color=RED)))
    _apply_dark_chart(fig, f"{selected} {area} -- {model_labels.get(model, model)}")
    st.plotly_chart(fig, key="fc_main", width="stretch")

    spacer()

    # Throughput forecast
    if "pred_throughput" in df.columns and df["pred_throughput"].notna().any():
        section_header("Throughput Forecast")
        fig_tp = go.Figure(go.Bar(
            x=df["target_ts"],
            y=df["pred_throughput"],
            marker=dict(color=BLUE_PRIMARY, opacity=0.9, line=dict(color=BORDER, width=1)),
            text=df["pred_throughput"],
            textposition="auto",
            textfont=dict(color=TEXT_PRIMARY),
        ))
        apply_chart_theme(
            fig_tp,
            title="Predicted Throughput",
            height=280,
            xaxis_title="Time",
            yaxis_title="Passengers",
        )
        st.plotly_chart(fig_tp, key="fc_throughput", width="stretch")

    spacer()

    # Data table + download
    section_header("Forecast Data")
    st.dataframe(df, key="fc_data_table", width="stretch", hide_index=True)
    st.download_button(
        "Download CSV", df.to_csv(index=False), "forecast.csv", "text/csv",
        key="fc_download",
    )

# ---------------------------------------------------------------------------
# Multi-airport comparison
# ---------------------------------------------------------------------------
else:
    section_header(f"All Airports -- {area} ({model_labels.get(model, model)})")
    fig = go.Figure()
    colours = [BLUE_PRIMARY, RED, GREEN, "#9b59b6", ORANGE]
    for idx, code in enumerate(AIRPORT_CODES):
        try:
            fc = get_forecast(demo_now, code, horizon, area, model)
            pts = fc.get("points", [])
            if pts:
                df_a = pd.DataFrame(pts)
                fig.add_trace(go.Scatter(
                    x=df_a["target_ts"], y=df_a["pred_wait_min"],
                    mode="lines+markers", name=code,
                    line=dict(color=colours[idx % len(colours)], width=2.5),
                    marker=dict(size=6),
                ))
        except Exception:
            continue
    fig.add_hline(y=10, line_dash="dash", line_color=RED, annotation_text="SLA 10 min",
                  annotation=dict(font=dict(color=RED)))
    _apply_dark_chart(fig, f"All Airports -- {area} -- {model_labels.get(model, model)}", 500)
    st.plotly_chart(fig, key="fc_multi_airport", width="stretch")
