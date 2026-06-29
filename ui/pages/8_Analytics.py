"""Page 8 -- Analytics & Reporting."""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api_client import (
    AIRPORT_CODES,
    DATA_MIN_DATE,
    DATA_MAX_DATE,
    render_alert_banner,
    render_sidebar,
    get_kpis,
    get_scorecard,
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
    BLUE_LIGHT,
    GREEN,
    YELLOW,
    RED,
    ORANGE,
)

st.set_page_config(page_title="Analytics & Reporting", layout="wide")
inject_theme()
airport, demo_now = render_sidebar()

# Page header
st.markdown(
    '<h1 style="color:#FAFAFA;font-weight:700;margin-bottom:4px;">Analytics & Reporting</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="color:#8B949E;font-size:0.95em;margin-bottom:24px;">'
    'Historical performance analysis, trend identification, and executive reporting</p>',
    unsafe_allow_html=True,
)
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
# 1. Executive Summary
# ---------------------------------------------------------------------------
section_header("Executive Summary")

avg_wait = kpis.get("avg_wait_min", 0)
p95_wait = kpis.get("p95_wait_min", 0)
total_pax = kpis.get("total_pax", 0)
breach_rate = kpis.get("sla_breach_rate", 0)
anomaly_count = kpis.get("anomaly_count", 0)
busiest = kpis.get("busiest_airport", "N/A")
busiest_h = kpis.get("busiest_hour", "N/A")

if breach_rate < 0.05:
    perf_assessment = "excellent"
    perf_colour = GREEN
elif breach_rate < 0.15:
    perf_assessment = "satisfactory"
    perf_colour = YELLOW
else:
    perf_assessment = "below target"
    perf_colour = RED

days_in_range = max((date_to - date_from).days, 1)
daily_avg_pax = total_pax / days_in_range

st.markdown(
    f'<div style="background:{SURFACE};border:1px solid {BORDER};'
    f'border-left:4px solid {perf_colour};border-radius:8px;padding:20px 24px;'
    f'line-height:1.7;margin-bottom:16px;">'
    f'<div style="color:{TEXT_PRIMARY};font-size:0.95em;">'
    f'For the period <span style="font-weight:600;">{date_from}</span> to '
    f'<span style="font-weight:600;">{date_to}</span> '
    f'({days_in_range} days), overall queue performance was '
    f'<span style="color:{perf_colour};font-weight:700;">{perf_assessment}</span> '
    f'with an average wait time of <span style="font-weight:600;">{avg_wait:.1f} min</span> and '
    f'P95 of <span style="font-weight:600;">{p95_wait:.1f} min</span>. '
    f'A total of <span style="font-weight:600;">{total_pax:,}</span> passengers were processed '
    f'(~{daily_avg_pax:,.0f}/day). '
    f'SLA breach rate was <span style="font-weight:600;">{breach_rate*100:.1f}%</span> with '
    f'<span style="font-weight:600;">{anomaly_count}</span> anomalies detected. '
    f'Peak activity was at <span style="font-weight:600;">{busiest}</span> airport during the '
    f'<span style="font-weight:600;">{busiest_h}:00</span> hour.</div>'
    f'</div>',
    unsafe_allow_html=True,
)

spacer()

# ---------------------------------------------------------------------------
# 2. KPI Cards with deltas
# ---------------------------------------------------------------------------
section_header("Key Metrics")

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

spacer()

# ---------------------------------------------------------------------------
# 3. Trend Charts in tabs
# ---------------------------------------------------------------------------
if trend:
    df_trend = pd.DataFrame(trend)
    df_trend["obs_date"] = pd.to_datetime(df_trend["obs_date"])

    section_header("Performance Trends")
    tab1, tab2, tab3 = st.tabs(["Wait Time", "Passenger Volume", "SLA Breach Rate"])

    with tab1:
        fig_wait = go.Figure()
        fig_wait.add_trace(go.Scatter(
            x=df_trend["obs_date"],
            y=df_trend["avg_wait_min"],
            mode="lines",
            name="Average Wait",
            line=dict(color=BLUE_PRIMARY, width=2.5),
            fill="tozeroy",
            fillcolor="rgba(0,128,255,0.08)",
        ))
        fig_wait.add_hline(
            y=10, line_dash="dash", line_color=RED,
            annotation_text="SLA Target",
            annotation=dict(font=dict(color=RED)),
        )
        if len(df_trend) >= 7:
            df_trend["ma7"] = df_trend["avg_wait_min"].rolling(7).mean()
            fig_wait.add_trace(go.Scatter(
                x=df_trend["obs_date"],
                y=df_trend["ma7"],
                mode="lines",
                name="7-day MA",
                line=dict(color=ORANGE, width=2.5, dash="dot"),
            ))
        apply_chart_theme(
            fig_wait,
            title="Average Wait Time Trend",
            height=380,
            xaxis_title="Date",
            yaxis_title="Wait (min)",
            legend=dict(orientation="h", y=-0.15, bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_SECONDARY)),
        )
        st.plotly_chart(fig_wait, key="analytics_wait_trend", width="stretch")

    with tab2:
        fig_pax = go.Figure(go.Bar(
            x=df_trend["obs_date"],
            y=df_trend["total_pax"],
            marker=dict(color=BLUE_PRIMARY, opacity=0.9, line=dict(color=BORDER, width=1)),
        ))
        apply_chart_theme(
            fig_pax,
            title="Daily Passenger Volume",
            height=380,
            xaxis_title="Date",
            yaxis_title="Passengers",
        )
        st.plotly_chart(fig_pax, key="analytics_pax_trend", width="stretch")

    with tab3:
        df_trend["breach_pct"] = df_trend["sla_breach_rate"] * 100
        fig_breach = go.Figure()
        fig_breach.add_trace(go.Scatter(
            x=df_trend["obs_date"],
            y=df_trend["breach_pct"],
            mode="lines",
            name="Breach Rate",
            line=dict(color=RED, width=2.5),
            fill="tozeroy",
            fillcolor="rgba(248,81,73,0.08)",
        ))
        fig_breach.add_hline(
            y=5, line_dash="dash", line_color=YELLOW,
            annotation_text="5% Target",
            annotation=dict(font=dict(color=YELLOW)),
        )
        apply_chart_theme(
            fig_breach,
            title="SLA Breach Rate Trend",
            height=380,
            xaxis_title="Date",
            yaxis_title="Breach %",
        )
        st.plotly_chart(fig_breach, key="analytics_breach_trend", width="stretch")

spacer()

# ---------------------------------------------------------------------------
# 4. Airport Ranking (when All is selected)
# ---------------------------------------------------------------------------
if ap == "ALL":
    section_header("Airport Ranking")
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
                marker=dict(
                    color=[
                        GREEN if w < 7 else YELLOW if w < 10 else RED
                        for w in df_rank["avg_wait"]
                    ],
                    opacity=0.9,
                    line=dict(color=BORDER, width=1),
                ),
                text=[f"{w:.1f}" for w in df_rank["avg_wait"]],
                textposition="auto",
                textfont=dict(color=TEXT_PRIMARY),
            ))
            fig_rank_wait.add_hline(
                y=10, line_dash="dash", line_color=RED,
                annotation_text="SLA",
                annotation=dict(font=dict(color=RED)),
            )
            apply_chart_theme(
                fig_rank_wait,
                title="Average Wait by Airport",
                height=350,
                xaxis_title="Airport",
                yaxis_title="Wait (min)",
            )
            st.plotly_chart(fig_rank_wait, key="analytics_rank_wait", width="stretch")

        with col_r2:
            fig_rank_breach = go.Figure(go.Bar(
                x=df_rank["airport"],
                y=df_rank["breach_rate"],
                marker=dict(
                    color=[
                        GREEN if b < 5 else YELLOW if b < 15 else RED
                        for b in df_rank["breach_rate"]
                    ],
                    opacity=0.9,
                    line=dict(color=BORDER, width=1),
                ),
                text=[f"{b:.1f}%" for b in df_rank["breach_rate"]],
                textposition="auto",
                textfont=dict(color=TEXT_PRIMARY),
            ))
            apply_chart_theme(
                fig_rank_breach,
                title="SLA Breach Rate by Airport",
                height=350,
                xaxis_title="Airport",
                yaxis_title="Breach %",
            )
            st.plotly_chart(fig_rank_breach, key="analytics_rank_breach", width="stretch")

        st.dataframe(
            df_rank.sort_values("avg_wait"),
            key="analytics_rank_table",
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("Could not load per-airport KPIs for ranking.")

spacer()

# ---------------------------------------------------------------------------
# 5. Export
# ---------------------------------------------------------------------------
section_header("Export Data")
if trend:
    st.download_button(
        "Download Trend CSV",
        df_trend.to_csv(index=False),
        "analytics_trend.csv",
        "text/csv",
        key="analytics_download",
    )
else:
    st.info("No trend data available for this range.")

spacer()

# ---------------------------------------------------------------------------
# 6. Daily Scorecard
# ---------------------------------------------------------------------------
section_header("Daily Scorecard")
scorecard_ap = ap if ap != "ALL" else "ATL"
try:
    sc = get_scorecard(demo_now, scorecard_ap, str(date_from))
    if sc:
        score_colors = {"EXCELLENT": GREEN, "GOOD": BLUE_PRIMARY, "FAIR": YELLOW, "POOR": RED}
        sc_color = score_colors.get(sc["overall_score"], TEXT_MUTED)
        st.markdown(
            f'<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;'
            f'padding:24px;text-align:center;margin-bottom:16px;">'
            f'<div style="font-size:0.8em;color:{TEXT_MUTED};text-transform:uppercase;'
            f'letter-spacing:0.05em;">{sc["airport_code"]} -- {sc["date"]}</div>'
            f'<div style="display:inline-flex;align-items:center;justify-content:center;'
            f'width:80px;height:80px;border-radius:50%;border:3px solid {sc_color};'
            f'margin:12px 0;">'
            f'<span style="font-size:1.2em;font-weight:800;color:{sc_color};">'
            f'{sc["overall_score"]}</span></div>'
            f'<div style="font-size:0.9em;color:{TEXT_SECONDARY};margin-top:8px;">'
            f'SLA Compliance: <span style="color:{TEXT_PRIMARY};font-weight:600;">'
            f'{sc["sla_compliance_pct"]:.0f}%</span> | '
            f'Avg Wait: <span style="color:{TEXT_PRIMARY};font-weight:600;">'
            f'{sc["avg_wait_min"]:.1f} min</span> | '
            f'Pax: <span style="color:{TEXT_PRIMARY};font-weight:600;">'
            f'{sc["total_pax"]:,}</span> | '
            f'Anomalies: <span style="color:{TEXT_PRIMARY};font-weight:600;">'
            f'{sc["anomaly_count"]}</span></div></div>',
            unsafe_allow_html=True,
        )
        if sc.get("areas"):
            sc_cols = st.columns(min(len(sc["areas"]), 4))
            for i, area_sc in enumerate(sc["areas"]):
                with sc_cols[i % len(sc_cols)]:
                    a_color = GREEN if area_sc["sla_compliance_pct"] >= 90 else YELLOW if area_sc["sla_compliance_pct"] >= 70 else RED
                    st.markdown(
                        f'<div style="background:{SURFACE};border:1px solid {BORDER};'
                        f'border-left:4px solid {a_color};border-radius:8px;'
                        f'padding:12px 16px;text-align:center;margin-bottom:6px;">'
                        f'<div style="font-size:0.8em;color:{TEXT_SECONDARY};text-transform:uppercase;'
                        f'letter-spacing:0.05em;">{area_sc["area_type"]}</div>'
                        f'<div style="font-size:1.6em;font-weight:700;color:{TEXT_PRIMARY};margin:6px 0 2px 0;">'
                        f'{area_sc["sla_compliance_pct"]:.0f}%</div>'
                        f'<div style="font-size:0.75em;color:{TEXT_MUTED};">SLA compliance</div>'
                        f'<div style="font-size:0.7em;color:{TEXT_MUTED};margin-top:4px;">'
                        f'Peak: {area_sc["peak_wait_min"]:.0f}m | {area_sc["total_pax"]:,} pax</div></div>',
                        unsafe_allow_html=True,
                    )
except Exception:
    pass
