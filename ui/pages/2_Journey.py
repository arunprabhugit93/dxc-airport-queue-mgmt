"""Page 2 -- Passenger Journey."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from api_client import (
    AIRPORT_CODES,
    render_alert_banner,
    render_sidebar,
    get_passenger_journey,
)
from theme import (
    inject_theme,
    section_header,
    metric_card,
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
)

st.set_page_config(page_title="Passenger Journey", layout="wide")
inject_theme()
airport, demo_now = render_sidebar()

# Page header
st.markdown(
    '<h1 style="color:#FAFAFA;font-weight:700;margin-bottom:4px;">Passenger Journey</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="color:#8B949E;font-size:0.95em;margin-bottom:24px;">'
    'Visualise the end-to-end passenger experience from arrival to boarding</p>',
    unsafe_allow_html=True,
)
render_alert_banner(demo_now, airport)

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.divider()
    selected_airport = st.selectbox(
        "Airport for journey view",
        AIRPORT_CODES,
        index=0,
        key="journey_airport",
    )
    compare_mode = st.toggle("Compare all airports", key="journey_compare")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STATUS_COLOUR = {"OK": GREEN, "WARNING": YELLOW, "BREACH": RED}

STAGE_ORDER = ["CHECKIN", "SECURITY_TSA", "SECURITY_PRECHECK", "IMMIGRATION", "GATE", "BOARDING"]
STAGE_LABELS = {
    "CHECKIN": "Check-in",
    "SECURITY_TSA": "Security (TSA)",
    "SECURITY_PRECHECK": "Security (PreCheck)",
    "IMMIGRATION": "Immigration",
    "GATE": "Gate Area",
    "BOARDING": "Boarding",
}


def _hex_to_rgba(hex_color: str, alpha: float = 0.4) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _render_journey(airport_code: str) -> None:
    """Render full journey dashboard for one airport."""
    try:
        data = get_passenger_journey(demo_now, airport_code)
    except Exception:
        data = None

    if data is None:
        st.info(
            f"Journey data for {airport_code} is not yet available. "
            "The /passenger-journey endpoint may not be deployed."
        )
        return

    stages = data.get("stages", [])
    total_journey = data.get("total_journey_min", 0)
    bottleneck = data.get("bottleneck", "Unknown")

    if not stages:
        st.info(f"No journey stage data available for {airport_code}.")
        return

    # --- Bottleneck callout ---
    bottleneck_stage = next(
        (s for s in stages if s["stage"] == bottleneck), None
    )
    if bottleneck_stage:
        bn_wait = bottleneck_stage["avg_wait_min"]
        bn_status = bottleneck_stage.get("status", "WARNING")
        bn_colour = STATUS_COLOUR.get(bn_status, YELLOW)
        st.markdown(
            f'<div style="background:{SURFACE};border:1px solid {BORDER};'
            f'border-left:4px solid {bn_colour};border-radius:8px;padding:16px 20px;margin-bottom:16px;">'
            f'<div style="color:{bn_colour};font-weight:700;font-size:1.1em;margin-bottom:4px;">'
            f'Bottleneck: {STAGE_LABELS.get(bottleneck, bottleneck)}</div>'
            f'<div style="color:{TEXT_SECONDARY};font-size:0.95em;">'
            f'Average wait <span style="color:{TEXT_PRIMARY};font-weight:600;">{bn_wait:.1f} min</span>'
            f' -- this stage is currently the longest delay in the passenger journey.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # --- Journey summary ---
    stage_parts = []
    for s in stages:
        label = STAGE_LABELS.get(s["stage"], s["stage"])
        stage_parts.append(f"{s['avg_wait_min']:.0f} min {label.lower()}")
    summary = ", ".join(stage_parts)
    st.markdown(
        f'<p style="color:{TEXT_SECONDARY};font-size:0.95em;">A passenger arriving now will spend: '
        f'<span style="color:{TEXT_PRIMARY};font-weight:600;">{summary}</span> = '
        f'<span style="color:{BLUE_PRIMARY};font-weight:700;">{total_journey:.0f} min total.</span></p>',
        unsafe_allow_html=True,
    )

    spacer(16)

    col_sankey, col_timeline = st.columns([3, 2])

    # --- Sankey Diagram ---
    with col_sankey:
        section_header("Passenger Flow")
        node_labels = ["Arrival"]
        node_colours = [BLUE_PRIMARY]
        for s in stages:
            node_labels.append(STAGE_LABELS.get(s["stage"], s["stage"]))
            node_colours.append(STATUS_COLOUR.get(s.get("status", "OK"), GREEN))

        source_indices = list(range(len(stages)))
        target_indices = list(range(1, len(stages) + 1))
        values = [max(s.get("queue_length", 50), 10) for s in stages]

        link_colours = [
            _hex_to_rgba(STATUS_COLOUR.get(s.get("status", "OK"), GREEN), 0.4)
            for s in stages
        ]

        fig_sankey = go.Figure(go.Sankey(
            node=dict(
                pad=20,
                thickness=25,
                label=node_labels,
                color=node_colours,
            ),
            link=dict(
                source=source_indices,
                target=target_indices,
                value=values,
                color=link_colours,
            ),
        ))
        fig_sankey.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT_SECONDARY),
        )
        st.plotly_chart(fig_sankey, key="journey_sankey", width="stretch")

    # --- Journey Timeline (horizontal bar) ---
    with col_timeline:
        section_header("Cumulative Time")
        stage_names = [STAGE_LABELS.get(s["stage"], s["stage"]) for s in stages]
        wait_times = [s["avg_wait_min"] for s in stages]
        bar_colours = [STATUS_COLOUR.get(s.get("status", "OK"), GREEN) for s in stages]

        fig_bar = go.Figure(go.Bar(
            y=stage_names,
            x=wait_times,
            orientation="h",
            marker=dict(color=bar_colours, opacity=0.9, line=dict(color=BORDER, width=1)),
            text=[f"{w:.1f} min" for w in wait_times],
            textposition="auto",
            textfont=dict(color=TEXT_PRIMARY),
        ))
        apply_chart_theme(
            fig_bar,
            height=400,
            xaxis_title="Wait Time (min)",
            yaxis=dict(autorange="reversed", gridcolor=BORDER, linecolor=BORDER),
        )
        st.plotly_chart(fig_bar, key="journey_timeline", width="stretch")

    spacer()

    # --- Per-stage detail cards ---
    section_header("Stage Details")
    cols = st.columns(min(len(stages), 4))
    for idx, s in enumerate(stages):
        col = cols[idx % len(cols)]
        status = s.get("status", "OK")
        colour = STATUS_COLOUR.get(status, TEXT_MUTED)
        label = STAGE_LABELS.get(s["stage"], s["stage"])
        with col:
            st.markdown(
                f'<div style="background:{SURFACE};border:1px solid {BORDER};'
                f'border-left:4px solid {colour};border-radius:8px;'
                f'padding:16px;text-align:center;margin-bottom:10px;">'
                f'<div style="font-size:0.8em;color:{TEXT_SECONDARY};text-transform:uppercase;'
                f'letter-spacing:0.05em;">{label}</div>'
                f'<div style="font-size:2em;font-weight:700;color:{TEXT_PRIMARY};margin:8px 0 4px 0;">'
                f'{s["avg_wait_min"]:.1f}</div>'
                f'<div style="font-size:0.8em;color:{TEXT_MUTED};">min wait</div>'
                f'<div style="font-size:0.8em;color:{TEXT_MUTED};margin-top:4px;">'
                f'{s.get("queue_length", "?")} in queue</div>'
                f'<div style="margin-top:6px;">{status_badge(status)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
if not compare_mode:
    _render_journey(selected_airport)
else:
    section_header("Cross-Airport Comparison")
    comparison_data = []
    for code in AIRPORT_CODES:
        try:
            jdata = get_passenger_journey(demo_now, code)
            if jdata and jdata.get("total_journey_min"):
                comparison_data.append({
                    "airport": code,
                    "total_min": jdata["total_journey_min"],
                    "bottleneck": jdata.get("bottleneck", "?"),
                    "stages": jdata.get("stages", []),
                })
        except Exception:
            continue

    if not comparison_data:
        st.info(
            "Journey data is not yet available for any airport. "
            "The /passenger-journey endpoint may not be deployed."
        )
    else:
        fig_compare = go.Figure()
        colors = [BLUE_PRIMARY, RED, GREEN, "#9b59b6", ORANGE]
        for idx, entry in enumerate(comparison_data):
            stage_labels = [
                STAGE_LABELS.get(s["stage"], s["stage"]) for s in entry["stages"]
            ]
            stage_waits = [s["avg_wait_min"] for s in entry["stages"]]
            fig_compare.add_trace(go.Bar(
                name=entry["airport"],
                x=stage_labels,
                y=stage_waits,
                marker=dict(color=colors[idx % len(colors)], opacity=0.9),
            ))
        apply_chart_theme(
            fig_compare,
            title="Journey Stage Wait Times by Airport",
            height=450,
            barmode="group",
            xaxis_title="Stage",
            yaxis_title="Wait (min)",
        )
        st.plotly_chart(fig_compare, key="journey_compare", width="stretch")

        spacer(12)

        for entry in comparison_data:
            bottleneck_label = STAGE_LABELS.get(
                entry["bottleneck"], entry["bottleneck"]
            )
            st.markdown(
                f'<div style="color:{TEXT_SECONDARY};font-size:0.9em;margin-bottom:4px;">'
                f'<span style="color:{TEXT_PRIMARY};font-weight:600;">{entry["airport"]}</span>: '
                f'Total journey <span style="color:{BLUE_PRIMARY};font-weight:600;">'
                f'{entry["total_min"]:.0f} min</span> -- bottleneck at {bottleneck_label}</div>',
                unsafe_allow_html=True,
            )
