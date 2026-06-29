"""Page 8 -- Analytics & Reporting."""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from api_client import (
    AIRPORT_CODES,
    DATA_MIN_DATE,
    DATA_MAX_DATE,
    SLA_COLOUR,
    render_alert_banner,
    render_sidebar,
    get_kpis,
)

st.set_page_config(page_title="Analytics & Reporting", layout="wide", page_icon="✈️")
airport, demo_now = render_sidebar()

st.title("Analytics & Reporting")
st.caption("Historical performance analysis, trend identification, and executive reporting")
render_alert_banner(demo_now, airport)

with st.sidebar:
    st.divider()
    date_from = st.date_input(
        "From", value=date(2022, 1, 1), key="analytics_from",
        min_value=DATA_MIN_DATE, max_value=DATA_MAX_DATE,
    )
    date_to = st.date_input(
        "To", value=date(2022, 10, 15), key="analytics_to",
        min_value=DATA_MIN_DATE, max_value=DATA_MAX_DATE,
    )

ap = airport if airport != "All" else "ALL"

try:
    data = get_kpis(demo_now, str(date_from), str(date_to), ap)
except Exception as e:
    st.error(f"API error: {e}")
    st.stop()

kpis = data.get("kpis", {})
trend = data.get("trend", [])

# ---------------------------------------------------------------------------
# 1. Executive Summary (auto-generated)
# ---------------------------------------------------------------------------
st.subheader("Executive Summary")

avg_wait = kpis.get("avg_wait_min", 0)
p95_wait = kpis.get("p95_wait_min", 0)
total_pax = kpis.get("total_pax", 0)
breach_rate = kpis.get("sla_breach_rate", 0)
anomaly_count = kpis.get("anomaly_count", 0)
busiest = kpis.get("busiest_airport", "N/A")
busiest_h = kpis.get("busiest_hour", "N/A")

# Overall performance assessment
if breach_rate < 0.05:
    perf_assessment = "**excellent**"
    perf_colour = "#2ecc71"
elif breach_rate < 0.15:
    perf_assessment = "**satisfactory**"
    perf_colour = "#f39c12"
else:
    perf_assessment = "**below target**"
    perf_colour = "#e74c3c"

days_in_range = max((date_to - date_from).days, 1)
daily_avg_pax = total_pax / days_in_range

st.markdown(
    f'<div style="border-left:4px solid {perf_colour};padding:12px 18px;'
    f'background:#f9f9f9;border-radius:4px;margin-bottom:16px;line-height:1.6;">'
    f'For the period <strong>{date_from}</strong> to <strong>{date_to}</strong> '
    f'({days_in_range} days), overall queue performance was {perf_assessment} '
    f'with an average wait time of <strong>{avg_wait:.1f} min</strong> and '
    f'P95 of <strong>{p95_wait:.1f} min</strong>. '
    f'A total of <strong>{total_pax:,}</strong> passengers were processed '
    f'(~{daily_avg_pax:,.0f}/day). '
    f'SLA breach rate was <strong>{breach_rate*100:.1f}%</strong> with '
    f'<strong>{anomaly_count}</strong> anomalies detected. '
    f'Peak activity was at <strong>{busiest}</strong> airport during the '
    f'<strong>{busiest_h}:00</strong> hour.'
    f'</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 2. KPI Cards with deltas
# ---------------------------------------------------------------------------
st.subheader("Key Metrics")

# Try to compute deltas against a reference period (same-length period prior)
delta_avg = None
delta_breach = None
delta_pax = None
try:
    prior_days = (date_to - date_from).days
    prior_from = date_from - pd.Timedelta(days=prior_days)
    prior_to = date_from - pd.Timedelta(days=1)
    if prior_from >= DATA_MIN_DATE:
        prior_data = get_kpis(demo_now, str(prior_from), str(prior_to), ap)
        prior_kpis = prior_data.get("kpis", {})
        if prior_kpis:
            delta_avg = avg_wait - prior_kpis.get("avg_wait_min", avg_wait)
            delta_breach = (breach_rate - prior_kpis.get("sla_breach_rate", breach_rate)) * 100
            delta_pax = total_pax - prior_kpis.get("total_pax", total_pax)
except Exception:
    pass

c1, c2, c3 = st.columns(3)
c1.metric(
    "Avg Wait (min)", f"{avg_wait:.1f}",
    delta=f"{delta_avg:+.1f} vs prior" if delta_avg is not None else None,
    delta_color="inverse",
)
c2.metric(
    "P95 Wait (min)", f"{p95_wait:.1f}",
)
c3.metric(
    "Total Passengers", f"{total_pax:,}",
    delta=f"{delta_pax:+,} vs prior" if delta_pax is not None else None,
    delta_color="normal",
)

c4, c5, c6 = st.columns(3)
c4.metric(
    "SLA Breach Rate", f"{breach_rate*100:.1f}%",
    delta=f"{delta_breach:+.1f}pp vs prior" if delta_breach is not None else None,
    delta_color="inverse",
)
c5.metric("Anomaly Count", anomaly_count)
c6.metric("Busiest", f"{busiest} @ {busiest_h}:00")

# ---------------------------------------------------------------------------
# 3. Trend Charts in tabs
# ---------------------------------------------------------------------------
if trend:
    df_trend = pd.DataFrame(trend)
    df_trend["obs_date"] = pd.to_datetime(df_trend["obs_date"])

    st.subheader("Performance Trends")
    tab1, tab2, tab3 = st.tabs(["Wait Time", "Passenger Volume", "SLA Breach Rate"])

    with tab1:
        fig_wait = go.Figure()
        fig_wait.add_trace(go.Scatter(
            x=df_trend["obs_date"],
            y=df_trend["avg_wait_min"],
            mode="lines",
            name="Average Wait",
            line=dict(color="#2980b9", width=2),
            fill="tozeroy",
            fillcolor="rgba(41,128,185,0.1)",
        ))
        fig_wait.add_hline(
            y=10, line_dash="dash", line_color="#e74c3c",
            annotation_text="SLA Target",
        )
        # Add 7-day moving average if enough data
        if len(df_trend) >= 7:
            df_trend["ma7"] = df_trend["avg_wait_min"].rolling(7).mean()
            fig_wait.add_trace(go.Scatter(
                x=df_trend["obs_date"],
                y=df_trend["ma7"],
                mode="lines",
                name="7-day MA",
                line=dict(color="#e67e22", width=2, dash="dot"),
            ))
        fig_wait.update_layout(
            height=380, xaxis_title="Date", yaxis_title="Wait (min)",
            title="Average Wait Time Trend",
            legend=dict(orientation="h", y=-0.15),
        )
        st.plotly_chart(fig_wait, width="stretch")

    with tab2:
        fig_pax = go.Figure(go.Bar(
            x=df_trend["obs_date"],
            y=df_trend["total_pax"],
            marker_color="#3498db",
        ))
        fig_pax.update_layout(
            height=380, xaxis_title="Date", yaxis_title="Passengers",
            title="Daily Passenger Volume",
        )
        st.plotly_chart(fig_pax, width="stretch")

    with tab3:
        df_trend["breach_pct"] = df_trend["sla_breach_rate"] * 100
        fig_breach = go.Figure()
        fig_breach.add_trace(go.Scatter(
            x=df_trend["obs_date"],
            y=df_trend["breach_pct"],
            mode="lines",
            name="Breach Rate",
            line=dict(color="#e74c3c", width=2),
            fill="tozeroy",
            fillcolor="rgba(231,76,60,0.1)",
        ))
        fig_breach.add_hline(
            y=5, line_dash="dash", line_color="#f39c12",
            annotation_text="5% Target",
        )
        fig_breach.update_layout(
            height=380, xaxis_title="Date", yaxis_title="Breach %",
            title="SLA Breach Rate Trend",
        )
        st.plotly_chart(fig_breach, width="stretch")

# ---------------------------------------------------------------------------
# 4. Airport Ranking (when All is selected)
# ---------------------------------------------------------------------------
if ap == "ALL":
    st.subheader("Airport Ranking")
    airport_kpis = []
    for code in AIRPORT_CODES:
        try:
            ap_data = get_kpis(demo_now, str(date_from), str(date_to), code)
            ap_kpis = ap_data.get("kpis", {})
            airport_kpis.append({
                "airport": code,
                "avg_wait": ap_kpis.get("avg_wait_min", 0),
                "breach_rate": ap_kpis.get("sla_breach_rate", 0) * 100,
                "total_pax": ap_kpis.get("total_pax", 0),
                "anomalies": ap_kpis.get("anomaly_count", 0),
            })
        except Exception:
            continue

    if airport_kpis:
        df_rank = pd.DataFrame(airport_kpis)

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            fig_rank_wait = go.Figure(go.Bar(
                x=df_rank["airport"],
                y=df_rank["avg_wait"],
                marker_color=[
                    "#2ecc71" if w < 7 else "#f39c12" if w < 10 else "#e74c3c"
                    for w in df_rank["avg_wait"]
                ],
                text=[f"{w:.1f}" for w in df_rank["avg_wait"]],
                textposition="auto",
            ))
            fig_rank_wait.add_hline(
                y=10, line_dash="dash", line_color="#e74c3c",
                annotation_text="SLA",
            )
            fig_rank_wait.update_layout(
                title="Average Wait by Airport",
                height=350, xaxis_title="Airport", yaxis_title="Wait (min)",
            )
            st.plotly_chart(fig_rank_wait, width="stretch")

        with col_r2:
            fig_rank_breach = go.Figure(go.Bar(
                x=df_rank["airport"],
                y=df_rank["breach_rate"],
                marker_color=[
                    "#2ecc71" if b < 5 else "#f39c12" if b < 15 else "#e74c3c"
                    for b in df_rank["breach_rate"]
                ],
                text=[f"{b:.1f}%" for b in df_rank["breach_rate"]],
                textposition="auto",
            ))
            fig_rank_breach.update_layout(
                title="SLA Breach Rate by Airport",
                height=350, xaxis_title="Airport", yaxis_title="Breach %",
            )
            st.plotly_chart(fig_rank_breach, width="stretch")

        # Ranking table
        st.dataframe(
            df_rank.sort_values("avg_wait"),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("Could not load per-airport KPIs for ranking.")

# ---------------------------------------------------------------------------
# 5. Download
# ---------------------------------------------------------------------------
st.subheader("Export Data")
if trend:
    st.download_button(
        "Download Trend CSV",
        df_trend.to_csv(index=False),
        "analytics_trend.csv",
        "text/csv",
    )
else:
    st.info("No trend data available for this range.")

# ---------------------------------------------------------------------------
# 6. Daily Scorecard
# ---------------------------------------------------------------------------
st.subheader("Daily Scorecard")
scorecard_ap = ap if ap != "ALL" else "ATL"
try:
    from api_client import get_scorecard
    sc = get_scorecard(demo_now, scorecard_ap, str(date_from))
    if sc:
        score_colors = {"EXCELLENT": "#2ecc71", "GOOD": "#3498db", "FAIR": "#f39c12", "POOR": "#e74c3c"}
        sc_color = score_colors.get(sc["overall_score"], "#95a5a6")
        st.markdown(
            f'<div style="border:3px solid {sc_color};border-radius:12px;'
            f'padding:20px;text-align:center;margin-bottom:16px;">'
            f'<div style="font-size:0.9em;color:#888;">{sc["airport_code"]} -- {sc["date"]}</div>'
            f'<div style="font-size:2.5em;font-weight:800;color:{sc_color};">{sc["overall_score"]}</div>'
            f'<div style="font-size:1em;margin-top:8px;">'
            f'SLA Compliance: {sc["sla_compliance_pct"]:.0f}% | '
            f'Avg Wait: {sc["avg_wait_min"]:.1f} min | '
            f'Pax: {sc["total_pax"]:,} | '
            f'Anomalies: {sc["anomaly_count"]}</div></div>',
            unsafe_allow_html=True,
        )
        if sc.get("areas"):
            sc_cols = st.columns(min(len(sc["areas"]), 4))
            for i, area in enumerate(sc["areas"]):
                with sc_cols[i % len(sc_cols)]:
                    a_color = "#2ecc71" if area["sla_compliance_pct"] >= 90 else "#f39c12" if area["sla_compliance_pct"] >= 70 else "#e74c3c"
                    st.markdown(
                        f'<div style="border:1px solid {a_color};border-radius:6px;'
                        f'padding:10px;text-align:center;margin-bottom:6px;">'
                        f'<div style="font-size:0.8em;color:#aaa;">{area["area_type"]}</div>'
                        f'<div style="font-size:1.4em;font-weight:700;color:{a_color};">'
                        f'{area["sla_compliance_pct"]:.0f}%</div>'
                        f'<div style="font-size:0.75em;">SLA compliance</div>'
                        f'<div style="font-size:0.7em;color:#888;">'
                        f'Peak: {area["peak_wait_min"]:.0f}m | {area["total_pax"]:,} pax</div></div>',
                        unsafe_allow_html=True,
                    )
except Exception:
    pass
