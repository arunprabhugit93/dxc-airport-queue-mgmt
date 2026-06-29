"""Page 3 -- Queue Intelligence."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from api_client import (
    AIRPORT_CODES,
    AREA_LABELS,
    AREA_TYPES,
    SLA_COLOUR,
    render_alert_banner,
    render_sidebar,
    get_all_area_queues,
    get_heatmap,
    get_queues_current,
)

st.set_page_config(page_title="Queue Intelligence", layout="wide", page_icon="✈️")
airport, demo_now = render_sidebar()

st.title("Queue Intelligence")
st.caption("Deep-dive into queue performance across all areas and time patterns")
render_alert_banner(demo_now, airport)

selected = airport if airport != "All" else "ATL"

with st.sidebar:
    st.divider()
    heatmap_area = st.selectbox(
        "Heatmap area", AREA_TYPES,
        format_func=lambda a: AREA_LABELS.get(a, a),
        key="queue_heatmap_area",
    )
    heatmap_days = st.slider(
        "Heatmap lookback (days)", 7, 90, 30, key="queue_heatmap_days",
    )

# ---------------------------------------------------------------------------
# 1. All-Areas Overview
# ---------------------------------------------------------------------------
st.subheader(f"All Queue Areas -- {selected}")

all_areas_data = get_all_area_queues(demo_now, selected)

if all_areas_data and all_areas_data.get("queues"):
    queues_all = all_areas_data["queues"]
    cols = st.columns(min(len(queues_all), 3))
    for idx, q in enumerate(queues_all):
        col = cols[idx % len(cols)]
        status = q.get("sla_status", "OK")
        colour = SLA_COLOUR.get(status, "#95a5a6")
        area_label = AREA_LABELS.get(q["area_type"], q["area_type"])
        with col:
            st.markdown(
                f'<div style="border:2px solid {colour};border-radius:8px;'
                f'padding:16px;margin-bottom:10px;">'
                f'<div style="font-weight:700;font-size:1.05em;">{area_label}</div>'
                f'<div style="display:flex;justify-content:space-between;margin-top:8px;">'
                f'<div style="text-align:center;">'
                f'<div style="font-size:1.8em;font-weight:700;color:{colour};">'
                f'{q["wait_min"]:.1f}</div>'
                f'<div style="font-size:0.8em;color:#888;">Wait (min)</div></div>'
                f'<div style="text-align:center;">'
                f'<div style="font-size:1.8em;font-weight:700;">{q["queue_length"]}</div>'
                f'<div style="font-size:0.8em;color:#888;">In Queue</div></div>'
                f'<div style="text-align:center;">'
                f'<div style="font-size:1.8em;font-weight:700;">{q["staff_on_duty"]}</div>'
                f'<div style="font-size:0.8em;color:#888;">Staff</div></div>'
                f'</div>'
                f'<div style="margin-top:8px;text-align:right;">'
                f'<span style="background:{colour};color:#fff;padding:2px 8px;'
                f'border-radius:4px;font-size:0.8em;">{status}</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Area comparison bar chart
    st.subheader("Area Comparison")
    area_names = [AREA_LABELS.get(q["area_type"], q["area_type"]) for q in queues_all]
    wait_vals = [q["wait_min"] for q in queues_all]
    bar_colours = [SLA_COLOUR.get(q.get("sla_status", "OK"), "#95a5a6") for q in queues_all]

    fig_compare = go.Figure(go.Bar(
        x=area_names,
        y=wait_vals,
        marker_color=bar_colours,
        text=[f"{w:.1f}" for w in wait_vals],
        textposition="auto",
    ))
    fig_compare.add_hline(y=10, line_dash="dash", line_color="#e74c3c", annotation_text="SLA 10 min")
    fig_compare.update_layout(
        height=350,
        xaxis_title="Area",
        yaxis_title="Wait (min)",
        title=f"{selected} -- Wait Time by Area",
    )
    st.plotly_chart(fig_compare, width="stretch")

else:
    # Fallback: use security-only queue data
    st.info("All-areas data not available. Showing security checkpoint data only.")
    try:
        fallback = get_queues_current(demo_now, selected)
        fb_queues = fallback.get("queues", [])
        if fb_queues:
            df_fb = pd.DataFrame(fb_queues)
            c1, c2 = st.columns(2)
            for idx, (_, q) in enumerate(df_fb.iterrows()):
                col = c1 if idx % 2 == 0 else c2
                with col:
                    st.metric(
                        f"{q['area_type']}",
                        f"{q['wait_min']:.1f} min",
                        delta=f"{q['pax_last_hour']} pax/hr",
                    )
        else:
            st.info("No queue data at this time.")
    except Exception:
        st.info("Queue data unavailable.")

# ---------------------------------------------------------------------------
# 2. Heatmap -- Wait Time by Hour x Day-of-Week
# ---------------------------------------------------------------------------
st.subheader(f"Wait-Time Heatmap -- {AREA_LABELS.get(heatmap_area, heatmap_area)}")

heatmap_data = get_heatmap(demo_now, selected, heatmap_area, heatmap_days)

if heatmap_data and heatmap_data.get("cells"):
    cells = heatmap_data["cells"]

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hours_range = list(range(24))

    # Build 7x24 matrix
    matrix = np.full((7, 24), np.nan)
    for cell in cells:
        dow = cell["day_of_week"]
        hr = cell["hour"]
        if 0 <= dow < 7 and 0 <= hr < 24:
            matrix[dow][hr] = cell["avg_wait_min"]

    fig_hm = go.Figure(go.Heatmap(
        z=matrix,
        x=[f"{h:02d}:00" for h in hours_range],
        y=day_names,
        colorscale=[
            [0.0, "#2ecc71"],
            [0.4, "#f1c40f"],
            [0.7, "#f39c12"],
            [1.0, "#e74c3c"],
        ],
        colorbar=dict(title="Wait (min)"),
        hovertemplate="Day: %{y}<br>Hour: %{x}<br>Avg Wait: %{z:.1f} min<extra></extra>",
    ))
    fig_hm.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="Hour of Day",
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig_hm, width="stretch")

    # Narrative
    if cells:
        max_cell = max(cells, key=lambda c: c["avg_wait_min"])
        day_name = day_names[max_cell["day_of_week"]] if max_cell["day_of_week"] < 7 else "?"
        st.markdown(
            f"Peak congestion: **{day_name} at {max_cell['hour']:02d}:00** "
            f"with average wait of **{max_cell['avg_wait_min']:.1f} min**. "
            f"Consider pre-positioning extra staff for this window."
        )
else:
    st.info(
        "Heatmap data not available. The /queues/heatmap endpoint "
        "may not be deployed yet."
    )

# ---------------------------------------------------------------------------
# 3. Historical Queue Trend (using existing current data)
# ---------------------------------------------------------------------------
st.subheader("Current Security Queue Snapshot")
try:
    current_data = get_queues_current(demo_now, selected)
    current_queues = current_data.get("queues", [])
    if current_queues:
        df_q = pd.DataFrame(current_queues)
        display_cols = [
            "airport_code", "area_type", "pax_last_hour", "lanes_open",
            "wait_min", "sla_status", "trend",
        ]
        show_cols = [c for c in display_cols if c in df_q.columns]
        st.dataframe(df_q[show_cols], width="stretch", hide_index=True)
    else:
        st.info("No current queue data available.")
except Exception:
    st.info("Could not load current queue data.")

# ---------------------------------------------------------------------------
# 4. Terminal Breakdown
# ---------------------------------------------------------------------------
st.subheader(f"Terminal Breakdown -- {selected}")
try:
    from api_client import get_airport_terminals
    term_data = get_airport_terminals(demo_now, selected)
    if term_data and term_data.get("terminals"):
        terminals = term_data["terminals"]
        cols = st.columns(min(len(terminals), 5))
        for i, t in enumerate(terminals):
            col = cols[i % len(cols)]
            colour = SLA_COLOUR.get(t["sla_status"], "#95a5a6")
            with col:
                st.markdown(
                    f'<div style="border:2px solid {colour};border-radius:8px;'
                    f'padding:12px;text-align:center;margin-bottom:8px;">'
                    f'<div style="font-size:0.85em;color:#aaa;">{t["terminal"]}</div>'
                    f'<div style="font-size:1.8em;font-weight:700;color:{colour};">'
                    f'{t["estimated_wait_min"]:.0f}</div>'
                    f'<div style="font-size:0.8em;">min wait</div>'
                    f'<div style="font-size:0.75em;color:#888;">'
                    f'{t["estimated_pax"]:,} pax</div></div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("Terminal data not available.")
except Exception:
    pass

# ---------------------------------------------------------------------------
# 5. Capacity Utilization
# ---------------------------------------------------------------------------
st.subheader(f"Capacity Utilization -- {selected}")
try:
    from api_client import get_capacity
    cap_data = get_capacity(demo_now, selected)
    if cap_data and cap_data.get("areas"):
        st.metric("Overall Utilization", f"{cap_data['overall_utilization_pct']:.0f}%")
        cap_areas = cap_data["areas"]
        fig_cap = go.Figure()
        area_names = [AREA_LABELS.get(a["area_type"], a["area_type"]) for a in cap_areas]
        utils = [a["utilization_pct"] for a in cap_areas]
        bar_colors = [
            "#e74c3c" if u > 90 else "#f39c12" if u > 75 else "#3498db" if u > 50 else "#2ecc71"
            for u in utils
        ]
        fig_cap.add_trace(go.Bar(
            x=area_names, y=utils, marker_color=bar_colors,
            text=[f"{u:.0f}%" for u in utils], textposition="auto",
        ))
        fig_cap.add_hline(y=90, line_dash="dash", line_color="#e74c3c", annotation_text="Critical (90%)")
        fig_cap.update_layout(
            height=300, yaxis_title="Utilization %", yaxis_range=[0, 110],
            title=f"{selected} -- Capacity Utilization by Area",
        )
        st.plotly_chart(fig_cap, width="stretch")
    else:
        st.info("Capacity data not available.")
except Exception:
    pass
