"""Page 2 -- Passenger Journey."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from api_client import (
    AIRPORT_CODES,
    SLA_COLOUR,
    render_alert_banner,
    render_sidebar,
    get_passenger_journey,
)

st.set_page_config(page_title="Passenger Journey", layout="wide", page_icon="✈️")
airport, demo_now = render_sidebar()

st.title("Passenger Journey")
st.caption("Visualise the end-to-end passenger experience from arrival to boarding")
render_alert_banner(demo_now, airport)

# ---------------------------------------------------------------------------
# Airport selector
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
# Helper: colour by status
# ---------------------------------------------------------------------------
STATUS_COLOUR = {"OK": "#2ecc71", "WARNING": "#f39c12", "BREACH": "#e74c3c"}

STAGE_ORDER = ["CHECKIN", "SECURITY_TSA", "SECURITY_PRECHECK", "IMMIGRATION", "GATE", "BOARDING"]
STAGE_LABELS = {
    "CHECKIN": "Check-in",
    "SECURITY_TSA": "Security (TSA)",
    "SECURITY_PRECHECK": "Security (PreCheck)",
    "IMMIGRATION": "Immigration",
    "GATE": "Gate Area",
    "BOARDING": "Boarding",
}


def _render_journey(airport_code: str) -> None:
    """Render full journey dashboard for one airport."""
    data = get_passenger_journey(demo_now, airport_code)

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
        bn_colour = STATUS_COLOUR.get(bn_status, "#f39c12")
        st.markdown(
            f'<div style="background:{bn_colour}22;border-left:5px solid {bn_colour};'
            f'padding:16px 20px;border-radius:4px;margin-bottom:16px;">'
            f'<h3 style="margin:0;color:{bn_colour};">Bottleneck: '
            f'{STAGE_LABELS.get(bottleneck, bottleneck)}</h3>'
            f'<p style="margin:4px 0 0 0;font-size:1.1em;">'
            f'Average wait <strong>{bn_wait:.1f} min</strong> &mdash; '
            f'this stage is currently the longest delay in the passenger journey.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # --- Journey summary sentence ---
    stage_parts = []
    for s in stages:
        label = STAGE_LABELS.get(s["stage"], s["stage"])
        stage_parts.append(f"{s['avg_wait_min']:.0f} min {label.lower()}")
    summary = ", ".join(stage_parts)
    st.markdown(
        f"A passenger arriving now will spend: **{summary}** = "
        f"**{total_journey:.0f} min total journey time.**"
    )

    col_sankey, col_timeline = st.columns([3, 2])

    # --- Sankey Diagram ---
    with col_sankey:
        st.subheader("Passenger Flow")
        node_labels = ["Arrival"]
        node_colours = ["#3498db"]
        for s in stages:
            node_labels.append(STAGE_LABELS.get(s["stage"], s["stage"]))
            node_colours.append(STATUS_COLOUR.get(s.get("status", "OK"), "#2ecc71"))

        source_indices = list(range(len(stages)))
        target_indices = list(range(1, len(stages) + 1))
        values = [max(s.get("queue_length", 50), 10) for s in stages]
        def _hex_to_rgba(hex_color: str, alpha: float = 0.35) -> str:
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"rgba({r},{g},{b},{alpha})"

        link_colours = [
            _hex_to_rgba(STATUS_COLOUR.get(s.get("status", "OK"), "#2ecc71"))
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
        )
        st.plotly_chart(fig_sankey, width="stretch")

    # --- Journey Timeline (horizontal bar) ---
    with col_timeline:
        st.subheader("Cumulative Time")
        stage_names = [STAGE_LABELS.get(s["stage"], s["stage"]) for s in stages]
        wait_times = [s["avg_wait_min"] for s in stages]
        bar_colours = [STATUS_COLOUR.get(s.get("status", "OK"), "#2ecc71") for s in stages]

        fig_bar = go.Figure(go.Bar(
            y=stage_names,
            x=wait_times,
            orientation="h",
            marker_color=bar_colours,
            text=[f"{w:.1f} min" for w in wait_times],
            textposition="auto",
        ))
        fig_bar.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Wait Time (min)",
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_bar, width="stretch")

    # --- Per-stage detail cards ---
    st.subheader("Stage Details")
    cols = st.columns(min(len(stages), 4))
    for idx, s in enumerate(stages):
        col = cols[idx % len(cols)]
        status = s.get("status", "OK")
        colour = STATUS_COLOUR.get(status, "#95a5a6")
        label = STAGE_LABELS.get(s["stage"], s["stage"])
        with col:
            st.markdown(
                f'<div style="border:2px solid {colour};border-radius:8px;'
                f'padding:14px;text-align:center;margin-bottom:10px;">'
                f'<div style="font-size:0.9em;color:#888;">{label}</div>'
                f'<div style="font-size:2em;font-weight:700;color:{colour};">'
                f'{s["avg_wait_min"]:.1f}</div>'
                f'<div style="font-size:0.85em;">min wait</div>'
                f'<div style="font-size:0.8em;color:#666;">'
                f'{s.get("queue_length", "?")} in queue</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
if not compare_mode:
    _render_journey(selected_airport)
else:
    st.subheader("Cross-Airport Comparison")
    comparison_data = []
    for code in AIRPORT_CODES:
        jdata = get_passenger_journey(demo_now, code)
        if jdata and jdata.get("total_journey_min"):
            comparison_data.append({
                "airport": code,
                "total_min": jdata["total_journey_min"],
                "bottleneck": jdata.get("bottleneck", "?"),
                "stages": jdata.get("stages", []),
            })

    if not comparison_data:
        st.info(
            "Journey data is not yet available for any airport. "
            "The /passenger-journey endpoint may not be deployed."
        )
    else:
        # Grouped bar: each airport, each stage
        fig_compare = go.Figure()
        for entry in comparison_data:
            stage_labels = [
                STAGE_LABELS.get(s["stage"], s["stage"]) for s in entry["stages"]
            ]
            stage_waits = [s["avg_wait_min"] for s in entry["stages"]]
            fig_compare.add_trace(go.Bar(
                name=entry["airport"],
                x=stage_labels,
                y=stage_waits,
            ))
        fig_compare.update_layout(
            barmode="group",
            title="Journey Stage Wait Times by Airport",
            xaxis_title="Stage",
            yaxis_title="Wait (min)",
            height=450,
        )
        st.plotly_chart(fig_compare, width="stretch")

        # Summary table
        for entry in comparison_data:
            bottleneck_label = STAGE_LABELS.get(
                entry["bottleneck"], entry["bottleneck"]
            )
            st.markdown(
                f"**{entry['airport']}**: Total journey "
                f"**{entry['total_min']:.0f} min** -- "
                f"bottleneck at {bottleneck_label}"
            )
