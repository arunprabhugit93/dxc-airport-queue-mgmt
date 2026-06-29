"""Page 3 -- Queue Intelligence."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api_client import (
    AIRPORT_CODES,
    AREA_LABELS,
    AREA_TYPES,
    SLA_COLOUR,
    render_alert_banner,
    render_theme_toggle,
    render_sidebar,
    get_all_area_queues,
    get_heatmap,
    get_queues_current,
    get_airport_terminals,
    get_capacity,
)
from theme import (
    inject_theme,
    section_header,
    status_badge,
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

st.set_page_config(page_title="Queue Intelligence", layout="wide")
inject_theme()
airport, demo_now = render_sidebar()

# Page header
st.markdown(
    '<h1 style="color:#FAFAFA;font-weight:700;margin-bottom:4px;">Queue Intelligence</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="color:#8B949E;font-size:0.95em;margin-bottom:24px;">'
    'Deep-dive into queue performance across all areas and time patterns</p>',
    unsafe_allow_html=True,
)
render_theme_toggle()
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
section_header(f"All Queue Areas -- {selected}")

try:
    all_areas_data = get_all_area_queues(demo_now, selected)
except Exception:
    all_areas_data = None

if all_areas_data and all_areas_data.get("queues"):
    queues_all = all_areas_data["queues"]
    cols = st.columns(min(len(queues_all), 3))
    for idx, q in enumerate(queues_all):
        col = cols[idx % len(cols)]
        status = q.get("sla_status", "OK")
        colour = SLA_COLOUR.get(status, TEXT_MUTED)
        area_label = AREA_LABELS.get(q["area_type"], q["area_type"])
        with col:
            st.markdown(
                f'<div style="background:{SURFACE};border:1px solid {BORDER};'
                f'border-left:4px solid {colour};border-radius:8px;'
                f'padding:16px 20px;margin-bottom:10px;">'
                f'<div style="font-weight:600;font-size:0.95em;color:{TEXT_PRIMARY};margin-bottom:10px;">'
                f'{area_label}</div>'
                f'<div style="display:flex;justify-content:space-between;gap:8px;">'
                f'<div style="text-align:center;">'
                f'<div style="font-size:1.8em;font-weight:700;color:{TEXT_PRIMARY};">'
                f'{q["wait_min"]:.1f}</div>'
                f'<div style="font-size:0.75em;color:{TEXT_MUTED};text-transform:uppercase;'
                f'letter-spacing:0.03em;">Wait (min)</div></div>'
                f'<div style="text-align:center;">'
                f'<div style="font-size:1.8em;font-weight:700;color:{TEXT_PRIMARY};">'
                f'{q["queue_length"]}</div>'
                f'<div style="font-size:0.75em;color:{TEXT_MUTED};text-transform:uppercase;'
                f'letter-spacing:0.03em;">In Queue</div></div>'
                f'<div style="text-align:center;">'
                f'<div style="font-size:1.8em;font-weight:700;color:{TEXT_PRIMARY};">'
                f'{q["staff_on_duty"]}</div>'
                f'<div style="font-size:0.75em;color:{TEXT_MUTED};text-transform:uppercase;'
                f'letter-spacing:0.03em;">Staff</div></div>'
                f'</div>'
                f'<div style="margin-top:10px;text-align:right;">{status_badge(status)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    spacer()

    # Area comparison bar chart
    section_header("Area Comparison")
    area_names = [AREA_LABELS.get(q["area_type"], q["area_type"]) for q in queues_all]
    wait_vals = [q["wait_min"] for q in queues_all]
    bar_colours = [SLA_COLOUR.get(q.get("sla_status", "OK"), TEXT_MUTED) for q in queues_all]

    fig_compare = go.Figure(go.Bar(
        x=area_names,
        y=wait_vals,
        marker=dict(color=bar_colours, opacity=0.9, line=dict(color=BORDER, width=1)),
        text=[f"{w:.1f}" for w in wait_vals],
        textposition="auto",
        textfont=dict(color=TEXT_PRIMARY),
    ))
    fig_compare.add_hline(y=10, line_dash="dash", line_color=RED, annotation_text="SLA 10 min",
                          annotation=dict(font=dict(color=RED)))
    apply_chart_theme(
        fig_compare,
        title=f"{selected} -- Wait Time by Area",
        height=350,
        xaxis_title="Area",
        yaxis_title="Wait (min)",
    )
    st.plotly_chart(fig_compare, key="queue_area_compare", width="stretch")

else:
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

spacer()

# ---------------------------------------------------------------------------
# 2. Heatmap
# ---------------------------------------------------------------------------
section_header(f"Wait-Time Heatmap -- {AREA_LABELS.get(heatmap_area, heatmap_area)}")

try:
    heatmap_data = get_heatmap(demo_now, selected, heatmap_area, heatmap_days)
except Exception:
    heatmap_data = None

if heatmap_data and heatmap_data.get("cells"):
    cells = heatmap_data["cells"]

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hours_range = list(range(24))

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
            [0.0, SURFACE],
            [0.4, YELLOW],
            [0.7, ORANGE],
            [1.0, RED],
        ],
        colorbar=dict(title="Wait (min)", tickfont=dict(color=TEXT_SECONDARY)),
        hovertemplate="Day: %{y}<br>Hour: %{x}<br>Avg Wait: %{z:.1f} min<extra></extra>",
    ))
    apply_chart_theme(
        fig_hm,
        height=350,
        xaxis_title="Hour of Day",
        yaxis=dict(autorange="reversed", gridcolor=BORDER, linecolor=BORDER),
    )
    st.plotly_chart(fig_hm, key="queue_heatmap", width="stretch")

    if cells:
        max_cell = max(cells, key=lambda c: c["avg_wait_min"])
        day_name = day_names[max_cell["day_of_week"]] if max_cell["day_of_week"] < 7 else "?"
        st.markdown(
            f'<p style="color:{TEXT_SECONDARY};font-size:0.9em;">'
            f'Peak congestion: <span style="color:{TEXT_PRIMARY};font-weight:600;">'
            f'{day_name} at {max_cell["hour"]:02d}:00</span> '
            f'with average wait of <span style="color:{RED};font-weight:600;">'
            f'{max_cell["avg_wait_min"]:.1f} min</span>. '
            f'Consider pre-positioning extra staff for this window.</p>',
            unsafe_allow_html=True,
        )
else:
    st.info("Heatmap data not available. The /queues/heatmap endpoint may not be deployed yet.")

spacer()

# ---------------------------------------------------------------------------
# 3. Current Queue Snapshot
# ---------------------------------------------------------------------------
section_header("Current Security Queue Snapshot")
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
        st.dataframe(df_q[show_cols], key="queue_snapshot_df", width="stretch", hide_index=True)
    else:
        st.info("No current queue data available.")
except Exception:
    st.info("Could not load current queue data.")

spacer()

# ---------------------------------------------------------------------------
# 4. Terminal Breakdown
# ---------------------------------------------------------------------------
section_header(f"Terminal Breakdown -- {selected}")
try:
    term_data = get_airport_terminals(demo_now, selected)
    if term_data and term_data.get("terminals"):
        terminals = term_data["terminals"]
        cols = st.columns(min(len(terminals), 5))
        for i, t in enumerate(terminals):
            col = cols[i % len(cols)]
            colour = SLA_COLOUR.get(t["sla_status"], TEXT_MUTED)
            with col:
                st.markdown(
                    f'<div style="background:{SURFACE};border:1px solid {BORDER};'
                    f'border-left:4px solid {colour};border-radius:8px;'
                    f'padding:14px;text-align:center;margin-bottom:8px;">'
                    f'<div style="font-size:0.8em;color:{TEXT_SECONDARY};text-transform:uppercase;'
                    f'letter-spacing:0.05em;">{t["terminal"]}</div>'
                    f'<div style="font-size:1.8em;font-weight:700;color:{TEXT_PRIMARY};margin:6px 0 2px 0;">'
                    f'{t["estimated_wait_min"]:.0f}</div>'
                    f'<div style="font-size:0.8em;color:{TEXT_MUTED};">min wait</div>'
                    f'<div style="font-size:0.75em;color:{TEXT_MUTED};margin-top:4px;">'
                    f'{t["estimated_pax"]:,} pax</div>'
                    f'<div style="margin-top:6px;">{status_badge(t["sla_status"])}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("Terminal data not available.")
except Exception:
    pass

spacer()

# ---------------------------------------------------------------------------
# 5. Capacity Utilization
# ---------------------------------------------------------------------------
section_header(f"Capacity Utilization -- {selected}")
try:
    cap_data = get_capacity(demo_now, selected)
    if cap_data and cap_data.get("areas"):
        overall = cap_data["overall_utilization_pct"]
        overall_color = RED if overall > 90 else YELLOW if overall > 75 else GREEN
        st.markdown(
            f'<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;'
            f'padding:16px 20px;display:inline-block;margin-bottom:16px;">'
            f'<div style="font-size:0.8em;color:{TEXT_SECONDARY};text-transform:uppercase;'
            f'letter-spacing:0.05em;">Overall Utilization</div>'
            f'<div style="font-size:2em;font-weight:700;color:{overall_color};">{overall:.0f}%</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        cap_areas = cap_data["areas"]
        area_names = [AREA_LABELS.get(a["area_type"], a["area_type"]) for a in cap_areas]
        utils = [a["utilization_pct"] for a in cap_areas]
        bar_colors = [
            RED if u > 90 else YELLOW if u > 75 else BLUE_PRIMARY if u > 50 else GREEN
            for u in utils
        ]

        fig_cap = go.Figure(go.Bar(
            x=area_names, y=utils,
            marker=dict(color=bar_colors, opacity=0.9, line=dict(color=BORDER, width=1)),
            text=[f"{u:.0f}%" for u in utils],
            textposition="auto",
            textfont=dict(color=TEXT_PRIMARY),
        ))
        fig_cap.add_hline(y=90, line_dash="dash", line_color=RED, annotation_text="Critical (90%)",
                          annotation=dict(font=dict(color=RED)))
        apply_chart_theme(
            fig_cap,
            title=f"{selected} -- Capacity Utilization by Area",
            height=300,
            yaxis_title="Utilization %",
            yaxis_range=[0, 110],
        )
        st.plotly_chart(fig_cap, key="queue_capacity", width="stretch")
    else:
        st.info("Capacity data not available.")
except Exception:
    pass
