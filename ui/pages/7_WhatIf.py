"""Page 7 -- Scenario Simulator."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from api_client import render_alert_banner, render_sidebar, simulate_what_if
from theme import (
    inject_theme,
    section_header,
    metric_card,
    spacer,
    gauge_figure,
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

st.set_page_config(page_title="Scenario Simulator", layout="wide")
inject_theme()
airport, demo_now = render_sidebar()

# Page header
st.markdown(
    '<h1 style="color:#FAFAFA;font-weight:700;margin-bottom:4px;">Scenario Simulator</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="color:#8B949E;font-size:0.95em;margin-bottom:24px;">'
    'Test operational changes before implementing them -- compare scenarios side by side</p>',
    unsafe_allow_html=True,
)
render_alert_banner(demo_now, airport)

selected = airport if airport != "All" else "ATL"

with st.sidebar:
    st.divider()
    area = st.selectbox(
        "Checkpoint", ["SECURITY_TSA", "SECURITY_PRECHECK"], key="wi_area",
    )
    num_lanes = st.slider("Lanes", 1, 20, 6, key="wi_lanes")
    precheck_ratio = st.slider(
        "PreCheck ratio", 0.0, 1.0, 0.2, step=0.05, key="wi_precheck",
    )
    service_rate = st.number_input(
        "Service rate (pax/min/lane)",
        value=3.0 if area == "SECURITY_TSA" else 6.0,
        min_value=0.5, max_value=20.0, step=0.5, key="wi_svcrate",
    )
    surge = st.slider("Surge multiplier", 0.5, 3.0, 1.0, step=0.1, key="wi_surge")
    duration = st.slider(
        "Duration (min)", 15, 240, 60, step=15, key="wi_duration",
    )
    use_current = st.toggle("Use current arrivals", value=True, key="wi_usecur")
    manual_rate = None
    if not use_current:
        manual_rate = st.number_input(
            "Arrival rate (pax/min)", value=10.0, min_value=0.1, key="wi_rate",
        )
    run_btn = st.button("Run Simulation", key="wi_btn")
    save_btn = st.button("Save to Comparison", key="wi_save")

# ---------------------------------------------------------------------------
# Session state for scenario comparison
# ---------------------------------------------------------------------------
if "saved_scenarios" not in st.session_state:
    st.session_state.saved_scenarios = []

if not run_btn:
    st.markdown(
        f'<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;'
        f'padding:20px;text-align:center;">'
        f'<div style="color:{TEXT_SECONDARY};font-size:0.95em;">'
        f'Configure the scenario in the sidebar and click '
        f'<span style="color:{BLUE_PRIMARY};font-weight:600;">Run Simulation</span>.'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    if st.session_state.saved_scenarios:
        spacer()
        section_header("Saved Scenarios")
        for s in st.session_state.saved_scenarios:
            sc = s["scenario"]
            st.markdown(
                f'<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;'
                f'padding:12px 16px;margin-bottom:6px;">'
                f'<span style="color:{TEXT_PRIMARY};font-weight:600;">{s["label"]}</span>'
                f'<span style="color:{TEXT_SECONDARY};margin-left:12px;">'
                f'Mean wait {sc["mean_wait_min"]:.1f} min, '
                f'P95 {sc["p95_wait_min"]:.1f} min, '
                f'Max queue {sc["max_queue_len"]}</span></div>',
                unsafe_allow_html=True,
            )
        if st.button("Clear Saved", key="wi_clear_early"):
            st.session_state.saved_scenarios = []
            st.rerun()
    st.stop()

body = {
    "airport_code": selected,
    "area_type": area,
    "use_current_arrivals": use_current,
    "arrival_rate_per_min": manual_rate,
    "num_lanes": num_lanes,
    "precheck_ratio": precheck_ratio,
    "service_rate_per_lane": service_rate,
    "surge_multiplier": surge,
    "duration_min": duration,
}

try:
    result = simulate_what_if(body)
except Exception as e:
    st.error(f"Simulation failed: {e}")
    st.stop()

baseline = result["baseline"]
scenario = result["scenario"]
delta = result["delta"]

# ---------------------------------------------------------------------------
# 1. Visual Before/After -- Gauge Charts
# ---------------------------------------------------------------------------
section_header("Baseline vs Scenario")

col_base, col_scen = st.columns(2)

with col_base:
    st.markdown(
        f'<div style="color:{TEXT_SECONDARY};font-weight:600;font-size:0.9em;text-transform:uppercase;'
        f'letter-spacing:0.05em;margin-bottom:8px;">BASELINE (Current Operations)</div>',
        unsafe_allow_html=True,
    )
    g1, g2 = st.columns(2)
    with g1:
        fig_bw = gauge_figure(
            baseline["mean_wait_min"], "Mean Wait (min)",
            max_val=30, good_threshold=7, warn_threshold=10, threshold_val=10,
        )
        st.plotly_chart(fig_bw, key="wi_gauge_base_mean", width="stretch")
    with g2:
        fig_bp = gauge_figure(
            baseline["p95_wait_min"], "P95 Wait (min)",
            max_val=40, good_threshold=10, warn_threshold=15, threshold_val=15,
        )
        st.plotly_chart(fig_bp, key="wi_gauge_base_p95", width="stretch")

with col_scen:
    st.markdown(
        f'<div style="color:{BLUE_PRIMARY};font-weight:600;font-size:0.9em;text-transform:uppercase;'
        f'letter-spacing:0.05em;margin-bottom:8px;">SCENARIO (Proposed Changes)</div>',
        unsafe_allow_html=True,
    )
    g3, g4 = st.columns(2)
    with g3:
        fig_sw = gauge_figure(
            scenario["mean_wait_min"], "Mean Wait (min)",
            max_val=30, good_threshold=7, warn_threshold=10, threshold_val=10,
        )
        st.plotly_chart(fig_sw, key="wi_gauge_scen_mean", width="stretch")
    with g4:
        fig_sp = gauge_figure(
            scenario["p95_wait_min"], "P95 Wait (min)",
            max_val=40, good_threshold=10, warn_threshold=15, threshold_val=15,
        )
        st.plotly_chart(fig_sp, key="wi_gauge_scen_p95", width="stretch")

spacer()

# Metric cards row
metrics = [
    ("Mean Wait (min)", "mean_wait_min"),
    ("P95 Wait (min)", "p95_wait_min"),
    ("Max Queue Length", "max_queue_len"),
    ("Lane Utilisation", "lane_utilisation"),
    ("SLA Breach (min)", "sla_breach_min"),
]

cols = st.columns(len(metrics))
for col, (label, key) in zip(cols, metrics):
    bval = baseline[key]
    sval = scenario[key]
    d = delta.get(key)
    delta_str = f"{d:+.1f}" if d is not None else None
    col.metric(
        label,
        f"{sval:.1f}" if isinstance(sval, float) else str(sval),
        delta_str,
        delta_color="inverse" if key != "lane_utilisation" else "normal",
    )

spacer()

# ---------------------------------------------------------------------------
# 2. Comparison Bar Chart
# ---------------------------------------------------------------------------
section_header("Side-by-Side Comparison")
compare_keys = ["mean_wait_min", "p95_wait_min", "max_queue_len", "sla_breach_min"]
compare_labels = ["Mean Wait", "P95 Wait", "Max Queue", "SLA Breach Min"]

fig = go.Figure()
fig.add_trace(go.Bar(
    x=compare_labels,
    y=[baseline[k] for k in compare_keys],
    name="Baseline",
    marker=dict(color=RED, opacity=0.9, line=dict(color=BORDER, width=1)),
    text=[f"{baseline[k]:.1f}" for k in compare_keys],
    textposition="auto",
    textfont=dict(color=TEXT_PRIMARY),
))
fig.add_trace(go.Bar(
    x=compare_labels,
    y=[scenario[k] for k in compare_keys],
    name="Scenario",
    marker=dict(color=BLUE_PRIMARY, opacity=0.9, line=dict(color=BORDER, width=1)),
    text=[f"{scenario[k]:.1f}" for k in compare_keys],
    textposition="auto",
    textfont=dict(color=TEXT_PRIMARY),
))
apply_chart_theme(
    fig,
    title="Baseline vs Scenario",
    height=380,
    barmode="group",
)
st.plotly_chart(fig, key="wi_compare_chart", width="stretch")

spacer()

# ---------------------------------------------------------------------------
# 3. Narrative Verdict
# ---------------------------------------------------------------------------
section_header("Operations Assessment")
d_wait = delta.get("mean_wait_min", 0)
d_breach = delta.get("sla_breach_min", 0)
lane_diff = scenario["num_lanes"] - baseline["num_lanes"]

if d_wait < -1:
    improvement_pct = abs(d_wait) / max(baseline["mean_wait_min"], 0.1) * 100
    st.markdown(
        f'<div style="background:#2EA04315;border:1px solid {GREEN};border-left:4px solid {GREEN};'
        f'border-radius:8px;padding:16px 20px;">'
        f'<div style="color:{GREEN};font-weight:700;font-size:0.9em;margin-bottom:6px;">'
        f'RECOMMENDATION: IMPLEMENT</div>'
        f'<div style="color:{TEXT_PRIMARY};font-size:0.95em;">'
        f'{"Adding" if lane_diff > 0 else "Adjusting"} lanes from '
        f'{baseline["num_lanes"]} to {scenario["num_lanes"]} reduces mean wait '
        f'by {abs(d_wait):.1f} min ({improvement_pct:.0f}% improvement) and '
        f'{"eliminates" if scenario["sla_breach_min"] == 0 else "reduces"} '
        f'SLA breaches by {abs(d_breach)} minutes. '
        f'This translates to better passenger experience and improved compliance metrics.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
elif d_wait < 0:
    st.markdown(
        f'<div style="background:{SURFACE};border:1px solid {YELLOW};border-left:4px solid {YELLOW};'
        f'border-radius:8px;padding:16px 20px;">'
        f'<div style="color:{YELLOW};font-weight:700;font-size:0.9em;margin-bottom:6px;">'
        f'MARGINAL IMPROVEMENT</div>'
        f'<div style="color:{TEXT_PRIMARY};font-size:0.95em;">'
        f'This scenario reduces mean wait by {abs(d_wait):.1f} min. The improvement is modest -- '
        f'consider whether the additional resource cost justifies the gain.</div></div>',
        unsafe_allow_html=True,
    )
elif d_wait == 0:
    st.markdown(
        f'<div style="background:{SURFACE};border:1px solid {BORDER};border-left:4px solid {TEXT_MUTED};'
        f'border-radius:8px;padding:16px 20px;">'
        f'<div style="color:{TEXT_SECONDARY};font-weight:700;font-size:0.9em;margin-bottom:6px;">'
        f'NO CHANGE</div>'
        f'<div style="color:{TEXT_PRIMARY};font-size:0.95em;">'
        f'The scenario produces the same wait time as baseline. '
        f'Consider adjusting parameters for impact.</div></div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div style="background:#F8514915;border:1px solid {RED};border-left:4px solid {RED};'
        f'border-radius:8px;padding:16px 20px;">'
        f'<div style="color:{RED};font-weight:700;font-size:0.9em;margin-bottom:6px;">'
        f'WARNING: DEGRADATION</div>'
        f'<div style="color:{TEXT_PRIMARY};font-size:0.95em;">'
        f'This scenario increases mean wait by {d_wait:.1f} min and adds {d_breach} minutes '
        f'of SLA breaches. This configuration would worsen operations. '
        f'Consider adding more lanes or increasing service rate.</div></div>',
        unsafe_allow_html=True,
    )

spacer()

# ---------------------------------------------------------------------------
# 4. Save scenario
# ---------------------------------------------------------------------------
if save_btn:
    if len(st.session_state.saved_scenarios) >= 3:
        st.warning("Maximum 3 saved scenarios. Clear existing ones first.")
    else:
        scenario_label = f"S{len(st.session_state.saved_scenarios) + 1}: {num_lanes}L / {surge}x surge"
        st.session_state.saved_scenarios.append({
            "label": scenario_label,
            "scenario": scenario,
            "baseline": baseline,
            "delta": delta,
            "params": body,
        })
        st.success(f"Saved scenario: {scenario_label}")

# Saved scenario comparison
if st.session_state.saved_scenarios:
    section_header("Saved Scenario Comparison")
    fig_comp = go.Figure()
    comp_keys = ["mean_wait_min", "p95_wait_min", "max_queue_len"]
    comp_labels = ["Mean Wait", "P95 Wait", "Max Queue"]
    colours = [BLUE_PRIMARY, "#e67e22", "#9b59b6"]

    for idx, saved in enumerate(st.session_state.saved_scenarios):
        fig_comp.add_trace(go.Bar(
            x=comp_labels,
            y=[saved["scenario"][k] for k in comp_keys],
            name=saved["label"],
            marker=dict(color=colours[idx % len(colours)], opacity=0.9, line=dict(color=BORDER, width=1)),
        ))

    apply_chart_theme(
        fig_comp,
        title="Saved Scenarios Comparison",
        height=350,
        barmode="group",
    )
    st.plotly_chart(fig_comp, key="wi_saved_compare", width="stretch")

    if st.button("Clear Saved Scenarios", key="wi_clear"):
        st.session_state.saved_scenarios = []
        st.rerun()
