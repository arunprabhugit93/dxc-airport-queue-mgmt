"""Page 7 -- Scenario Simulator."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from api_client import render_alert_banner, render_sidebar, simulate_what_if

st.set_page_config(page_title="Scenario Simulator", layout="wide", page_icon="✈️")
airport, demo_now = render_sidebar()

st.title("Scenario Simulator")
st.caption("Test operational changes before implementing them -- compare scenarios side by side")
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
    st.info("Configure the scenario in the sidebar and click **Run Simulation**.")

    # Show saved scenarios if any
    if st.session_state.saved_scenarios:
        st.subheader("Saved Scenarios")
        saved = st.session_state.saved_scenarios
        for s in saved:
            sc = s["scenario"]
            st.markdown(
                f"**{s['label']}**: Mean wait {sc['mean_wait_min']:.1f} min, "
                f"P95 {sc['p95_wait_min']:.1f} min, "
                f"Max queue {sc['max_queue_len']}"
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
st.subheader("Baseline vs Scenario")

col_base, col_scen = st.columns(2)

with col_base:
    st.markdown("**BASELINE** (Current Operations)")
    g1, g2 = st.columns(2)
    with g1:
        fig_bw = go.Figure(go.Indicator(
            mode="gauge+number",
            value=baseline["mean_wait_min"],
            title={"text": "Mean Wait"},
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
        fig_bw.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=10))
        st.plotly_chart(fig_bw, width="stretch")

    with g2:
        fig_bp = go.Figure(go.Indicator(
            mode="gauge+number",
            value=baseline["p95_wait_min"],
            title={"text": "P95 Wait"},
            gauge={
                "axis": {"range": [0, 40]},
                "bar": {"color": "#2c3e50"},
                "steps": [
                    {"range": [0, 10], "color": "#2ecc71"},
                    {"range": [10, 15], "color": "#f39c12"},
                    {"range": [15, 40], "color": "#e74c3c"},
                ],
            },
        ))
        fig_bp.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=10))
        st.plotly_chart(fig_bp, width="stretch")

with col_scen:
    st.markdown("**SCENARIO** (Proposed Changes)")
    g3, g4 = st.columns(2)
    with g3:
        fig_sw = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=scenario["mean_wait_min"],
            delta={"reference": baseline["mean_wait_min"], "decreasing": {"color": "#2ecc71"}},
            title={"text": "Mean Wait"},
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
        fig_sw.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=10))
        st.plotly_chart(fig_sw, width="stretch")

    with g4:
        fig_sp = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=scenario["p95_wait_min"],
            delta={"reference": baseline["p95_wait_min"], "decreasing": {"color": "#2ecc71"}},
            title={"text": "P95 Wait"},
            gauge={
                "axis": {"range": [0, 40]},
                "bar": {"color": "#2c3e50"},
                "steps": [
                    {"range": [0, 10], "color": "#2ecc71"},
                    {"range": [10, 15], "color": "#f39c12"},
                    {"range": [15, 40], "color": "#e74c3c"},
                ],
            },
        ))
        fig_sp.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=10))
        st.plotly_chart(fig_sp, width="stretch")

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

# ---------------------------------------------------------------------------
# 2. Comparison Bar Chart
# ---------------------------------------------------------------------------
st.subheader("Side-by-Side Comparison")
compare_keys = ["mean_wait_min", "p95_wait_min", "max_queue_len", "sla_breach_min"]
compare_labels = ["Mean Wait", "P95 Wait", "Max Queue", "SLA Breach Min"]
fig = go.Figure()
fig.add_trace(go.Bar(
    x=compare_labels,
    y=[baseline[k] for k in compare_keys],
    name="Baseline",
    marker_color="#e74c3c",
    text=[f"{baseline[k]:.1f}" for k in compare_keys],
    textposition="auto",
))
fig.add_trace(go.Bar(
    x=compare_labels,
    y=[scenario[k] for k in compare_keys],
    name="Scenario",
    marker_color="#2980b9",
    text=[f"{scenario[k]:.1f}" for k in compare_keys],
    textposition="auto",
))
fig.update_layout(barmode="group", height=380, title="Baseline vs Scenario")
st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# 3. Narrative Verdict
# ---------------------------------------------------------------------------
st.subheader("Operations Assessment")
d_wait = delta.get("mean_wait_min", 0)
d_breach = delta.get("sla_breach_min", 0)
lane_diff = scenario["num_lanes"] - baseline["num_lanes"]

if d_wait < -1:
    improvement_pct = abs(d_wait) / max(baseline["mean_wait_min"], 0.1) * 100
    st.success(
        f"**Recommendation: IMPLEMENT this change.** "
        f"{'Adding' if lane_diff > 0 else 'Adjusting'} lanes from "
        f"{baseline['num_lanes']} to {scenario['num_lanes']} reduces mean wait "
        f"by {abs(d_wait):.1f} min ({improvement_pct:.0f}% improvement) and "
        f"{'eliminates' if scenario['sla_breach_min'] == 0 else 'reduces'} "
        f"SLA breaches by {abs(d_breach)} minutes. "
        f"This translates to better passenger experience and improved "
        f"compliance metrics."
    )
elif d_wait < 0:
    st.info(
        f"**Marginal improvement.** This scenario reduces mean wait by "
        f"{abs(d_wait):.1f} min. The improvement is modest -- consider whether "
        f"the additional resource cost justifies the gain."
    )
elif d_wait == 0:
    st.info(
        "**No change in performance.** The scenario produces the same "
        "wait time as baseline. Consider adjusting parameters for impact."
    )
else:
    st.error(
        f"**Warning: DEGRADATION.** This scenario increases mean wait by "
        f"{d_wait:.1f} min and adds {d_breach} minutes of SLA breaches. "
        f"This configuration would worsen operations. Consider adding more "
        f"lanes or increasing service rate."
    )

# ---------------------------------------------------------------------------
# 4. Save scenario for comparison
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

# Show saved scenario comparison
if st.session_state.saved_scenarios:
    st.subheader("Saved Scenario Comparison")
    fig_comp = go.Figure()
    comp_keys = ["mean_wait_min", "p95_wait_min", "max_queue_len"]
    comp_labels = ["Mean Wait", "P95 Wait", "Max Queue"]
    colours = ["#3498db", "#e67e22", "#9b59b6"]

    for idx, saved in enumerate(st.session_state.saved_scenarios):
        fig_comp.add_trace(go.Bar(
            x=comp_labels,
            y=[saved["scenario"][k] for k in comp_keys],
            name=saved["label"],
            marker_color=colours[idx % len(colours)],
        ))

    fig_comp.update_layout(
        barmode="group", height=350,
        title="Saved Scenarios Comparison",
    )
    st.plotly_chart(fig_comp, width="stretch")

    if st.button("Clear Saved Scenarios", key="wi_clear"):
        st.session_state.saved_scenarios = []
        st.rerun()
