"""Page 2 -- Passenger Journey (rich infographic)."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from api_client import (
    AIRPORT_CODES,
    render_alert_banner,
    render_theme_toggle,
    render_sidebar,
    get_passenger_journey,
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
    BLUE_LIGHT,
    GREEN,
    YELLOW,
    RED,
    ORANGE,
)

st.set_page_config(page_title="Passenger Journey", layout="wide")
inject_theme()
airport, demo_now = render_sidebar()

st.markdown(
    '<h1 style="color:#FAFAFA;font-weight:700;margin-bottom:4px;">Passenger Journey</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="color:#8B949E;font-size:0.95em;margin-bottom:24px;">'
    'End-to-end passenger experience from curb to gate -- where time is spent, where bottlenecks form</p>',
    unsafe_allow_html=True,
)
render_theme_toggle()
render_alert_banner(demo_now, airport)

with st.sidebar:
    st.divider()
    selected_airport = st.selectbox("Airport", AIRPORT_CODES, index=0, key="journey_airport")
    compare_mode = st.toggle("Compare all airports", key="journey_compare")

STATUS_COLOUR = {"OK": GREEN, "WARNING": YELLOW, "BREACH": RED}
STAGE_LABELS = {
    "CHECKIN": "Check-in & Bag Drop",
    "SECURITY_TSA": "TSA Security Screening",
    "SECURITY_PRECHECK": "TSA PreCheck",
    "IMMIGRATION": "Immigration & Customs",
    "GATE": "Gate & Boarding",
    "BAGGAGE": "Baggage Claim",
}
STAGE_ICONS = {
    "CHECKIN": "01", "SECURITY_TSA": "02", "SECURITY_PRECHECK": "02",
    "IMMIGRATION": "03", "GATE": "04", "BAGGAGE": "05",
}
STAGE_DESC = {
    "CHECKIN": "Document verification, boarding pass issuance, checked luggage drop-off",
    "SECURITY_TSA": "ID check, X-ray screening, walk-through metal detector, divestiture",
    "SECURITY_PRECHECK": "Expedited screening for trusted travellers, no shoe/laptop removal",
    "IMMIGRATION": "Passport control, customs declaration, border protection clearance",
    "GATE": "Boarding zone queuing, final document check, jet bridge access",
    "BAGGAGE": "Carousel wait, bag retrieval, customs exit for arriving passengers",
}


def _hex_to_rgba(hex_color: str, alpha: float = 0.4) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _render_journey(airport_code: str) -> None:
    try:
        data = get_passenger_journey(demo_now, airport_code)
    except Exception:
        data = None

    if data is None:
        st.info(f"Journey data for {airport_code} is not yet available.")
        return

    stages = data.get("stages", [])
    total_journey = data.get("total_journey_min", 0)
    bottleneck = data.get("bottleneck", "Unknown")

    if not stages:
        st.info(f"No journey stage data for {airport_code}.")
        return

    # === HERO: Total Journey Time + Bottleneck ===
    bn_stage = next((s for s in stages if s["stage"] == bottleneck), None)
    bn_label = STAGE_LABELS.get(bottleneck, bottleneck)
    bn_wait = bn_stage["avg_wait_min"] if bn_stage else 0
    bn_colour = STATUS_COLOUR.get(bn_stage.get("status", "WARNING") if bn_stage else "WARNING", YELLOW)
    bn_pct = round(bn_wait / total_journey * 100) if total_journey > 0 else 0

    hero_left, hero_right = st.columns([1, 1])
    with hero_left:
        st.markdown(
            f'<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:12px;'
            f'padding:28px 32px;text-align:center;">'
            f'<div style="font-size:0.75em;color:{TEXT_MUTED};text-transform:uppercase;'
            f'letter-spacing:0.1em;margin-bottom:8px;">TOTAL JOURNEY TIME</div>'
            f'<div style="font-size:4em;font-weight:800;color:{TEXT_PRIMARY};line-height:1;">'
            f'{total_journey:.0f}</div>'
            f'<div style="font-size:1em;color:{TEXT_SECONDARY};margin-top:4px;">minutes curb to gate</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with hero_right:
        st.markdown(
            f'<div style="background:{SURFACE};border:1px solid {BORDER};border-left:4px solid {bn_colour};'
            f'border-radius:12px;padding:28px 32px;">'
            f'<div style="font-size:0.75em;color:{TEXT_MUTED};text-transform:uppercase;'
            f'letter-spacing:0.1em;margin-bottom:8px;">BOTTLENECK IDENTIFIED</div>'
            f'<div style="font-size:1.6em;font-weight:700;color:{bn_colour};margin-bottom:4px;">'
            f'{bn_label}</div>'
            f'<div style="font-size:2.2em;font-weight:800;color:{TEXT_PRIMARY};line-height:1;">'
            f'{bn_wait:.0f} min</div>'
            f'<div style="font-size:0.85em;color:{TEXT_SECONDARY};margin-top:6px;">'
            f'{bn_pct}% of total journey time -- '
            f'{STAGE_DESC.get(bottleneck, "")[:60]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    spacer(20)

    # === VISUAL JOURNEY PIPELINE ===
    section_header("Journey Pipeline")
    st.markdown(
        f'<p style="color:{TEXT_SECONDARY};font-size:0.9em;margin-bottom:16px;">'
        f'A passenger arriving at {airport_code} right now will pass through these stages. '
        f'Bar width shows proportional time spent at each step.</p>',
        unsafe_allow_html=True,
    )

    # Proportional horizontal pipeline bar
    pipeline_html = '<div style="display:flex;gap:3px;border-radius:8px;overflow:hidden;height:56px;">'
    for s in stages:
        pct = max(s["avg_wait_min"] / total_journey * 100, 3) if total_journey > 0 else 20
        colour = STATUS_COLOUR.get(s.get("status", "OK"), GREEN)
        label = STAGE_LABELS.get(s["stage"], s["stage"]).split("&")[0].strip()
        wait = s["avg_wait_min"]
        pipeline_html += (
            f'<div style="flex:{pct};background:{_hex_to_rgba(colour, 0.25)};'
            f'border:1px solid {colour};display:flex;flex-direction:column;'
            f'justify-content:center;align-items:center;padding:4px 2px;min-width:40px;">'
            f'<div style="font-size:0.65em;color:{TEXT_SECONDARY};white-space:nowrap;overflow:hidden;'
            f'text-overflow:ellipsis;max-width:100%;">{label}</div>'
            f'<div style="font-size:1.1em;font-weight:700;color:{colour};">{wait:.0f}m</div>'
            f'</div>'
        )
    pipeline_html += '</div>'
    st.markdown(pipeline_html, unsafe_allow_html=True)

    spacer(8)

    # Passenger narrative
    stage_parts = [f"{s['avg_wait_min']:.0f} min at {STAGE_LABELS.get(s['stage'], s['stage']).lower()}"
                   for s in stages]
    narrative = " → ".join(stage_parts)
    st.markdown(
        f'<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;'
        f'padding:14px 20px;font-size:0.9em;color:{TEXT_SECONDARY};">'
        f'<span style="color:{BLUE_LIGHT};font-weight:600;">Passenger timeline:</span> '
        f'{narrative} = <span style="color:{TEXT_PRIMARY};font-weight:700;">{total_journey:.0f} min total</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    spacer(20)

    # === PASSENGER FLOW INFOGRAPHIC ===
    section_header("Passenger Flow")

    cumulative = 0.0
    flow_html = (
        '<div style="display:flex;align-items:stretch;gap:0;margin:0 0 20px 0;">'
    )
    for i, s in enumerate(stages):
        label = STAGE_LABELS.get(s["stage"], s["stage"])
        short_label = label.split("(")[0].strip().split("&")[0].strip()
        status = s.get("status", "OK")
        colour = STATUS_COLOUR.get(status, GREEN)
        wait = s["avg_wait_min"]
        queue_len = s.get("queue_length", 0)
        cumulative += wait
        pct = round(wait / total_journey * 100) if total_journey > 0 else 20
        step_num = STAGE_ICONS.get(s["stage"], str(i + 1))

        flow_html += (
            # Arrow connector (skip before first)
            (f'<div style="display:flex;align-items:center;color:{BORDER};font-size:1.4em;'
             f'margin:0 -2px;">&#9654;</div>' if i > 0 else '')
            +
            # Stage card
            f'<div style="flex:1;background:{SURFACE};border:1px solid {BORDER};'
            f'border-top:3px solid {colour};border-radius:8px;padding:14px 10px;'
            f'text-align:center;min-width:0;">'

            # Step number
            f'<div style="width:28px;height:28px;border-radius:50%;background:{_hex_to_rgba(colour, 0.2)};'
            f'border:2px solid {colour};margin:0 auto 8px;display:flex;align-items:center;'
            f'justify-content:center;font-size:0.75em;font-weight:700;color:{colour};">{step_num}</div>'

            # Label
            f'<div style="font-size:0.75em;font-weight:600;color:{TEXT_PRIMARY};'
            f'margin-bottom:6px;line-height:1.2;min-height:2.4em;">{short_label}</div>'

            # Wait time (hero metric)
            f'<div style="font-size:1.8em;font-weight:800;color:{colour};line-height:1;">'
            f'{wait:.0f}</div>'
            f'<div style="font-size:0.65em;color:{TEXT_MUTED};margin-bottom:6px;">min wait</div>'

            # Queue depth mini-bar
            f'<div style="background:{BORDER};border-radius:3px;height:6px;margin:4px 8px;overflow:hidden;">'
            f'<div style="background:{colour};width:{min(pct * 2, 100)}%;height:100%;border-radius:3px;"></div>'
            f'</div>'

            # Queue count + cumulative
            f'<div style="font-size:0.7em;color:{TEXT_MUTED};">{queue_len:,} queued</div>'
            f'<div style="font-size:0.65em;color:{TEXT_MUTED};margin-top:2px;">+{cumulative:.0f}m total</div>'

            # Status badge
            f'<div style="margin-top:6px;">{status_badge(status)}</div>'

            f'</div>'
        )

    flow_html += '</div>'
    st.markdown(flow_html, unsafe_allow_html=True)

    spacer(20)

    # === STAGE DEEP-DIVE CARDS ===
    section_header("Stage-by-Stage Analysis")

    for s in stages:
        label = STAGE_LABELS.get(s["stage"], s["stage"])
        status = s.get("status", "OK")
        colour = STATUS_COLOUR.get(status, GREEN)
        wait = s["avg_wait_min"]
        queue_len = s.get("queue_length", 0)
        step_num = STAGE_ICONS.get(s["stage"], "?")
        desc = STAGE_DESC.get(s["stage"], "")
        pct_of_journey = round(wait / total_journey * 100) if total_journey > 0 else 0
        wait_bar_width = min(pct_of_journey * 2, 100)

        st.markdown(
            f'<div style="background:{SURFACE};border:1px solid {BORDER};border-left:4px solid {colour};'
            f'border-radius:8px;padding:18px 24px;margin-bottom:12px;display:flex;gap:24px;align-items:center;">'

            # Step number circle
            f'<div style="min-width:48px;height:48px;border-radius:50%;background:{_hex_to_rgba(colour, 0.2)};'
            f'border:2px solid {colour};display:flex;align-items:center;justify-content:center;'
            f'font-size:1.2em;font-weight:700;color:{colour};">{step_num}</div>'

            # Main content
            f'<div style="flex:1;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
            f'<div style="font-size:1.05em;font-weight:600;color:{TEXT_PRIMARY};">{label}</div>'
            f'<div>{status_badge(status)}</div>'
            f'</div>'
            f'<div style="font-size:0.8em;color:{TEXT_MUTED};margin-bottom:10px;">{desc}</div>'

            # Metrics row
            f'<div style="display:flex;gap:24px;margin-bottom:8px;">'
            f'<div><span style="font-size:1.6em;font-weight:700;color:{colour};">{wait:.1f}</span>'
            f'<span style="font-size:0.8em;color:{TEXT_MUTED};"> min wait</span></div>'
            f'<div><span style="font-size:1.6em;font-weight:700;color:{TEXT_PRIMARY};">{queue_len}</span>'
            f'<span style="font-size:0.8em;color:{TEXT_MUTED};"> in queue</span></div>'
            f'<div><span style="font-size:1.6em;font-weight:700;color:{TEXT_SECONDARY};">{pct_of_journey}%</span>'
            f'<span style="font-size:0.8em;color:{TEXT_MUTED};"> of journey</span></div>'
            f'</div>'

            # Wait time progress bar
            f'<div style="background:{BORDER};border-radius:4px;height:8px;overflow:hidden;">'
            f'<div style="background:{colour};width:{wait_bar_width}%;height:100%;border-radius:4px;'
            f'transition:width 0.3s ease;"></div>'
            f'</div>'

            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    spacer(20)

    # === WAIT TIME BREAKDOWN CHART ===
    section_header("Wait Time Breakdown")

    col_bar, col_pie = st.columns([3, 2])

    with col_bar:
        stage_names = [STAGE_LABELS.get(s["stage"], s["stage"]) for s in stages]
        wait_times = [s["avg_wait_min"] for s in stages]
        bar_colours = [STATUS_COLOUR.get(s.get("status", "OK"), GREEN) for s in stages]

        fig_bar = go.Figure(go.Bar(
            y=stage_names,
            x=wait_times,
            orientation="h",
            marker=dict(color=bar_colours, opacity=0.9, line=dict(color=BORDER, width=1)),
            text=[f"{w:.1f} min" for w in wait_times],
            textposition="outside",
            textfont=dict(color=TEXT_PRIMARY, size=12),
        ))
        fig_bar.add_vline(x=10, line_dash="dash", line_color=RED,
                          annotation_text="SLA 10 min", annotation=dict(font=dict(color=RED, size=10)))
        apply_chart_theme(
            fig_bar, height=300,
            xaxis_title="Wait Time (min)",
            yaxis=dict(autorange="reversed", gridcolor=BORDER, linecolor=BORDER),
        )
        st.plotly_chart(fig_bar, key="journey_bar", width="stretch")

    with col_pie:
        fig_pie = go.Figure(go.Pie(
            labels=stage_names,
            values=wait_times,
            hole=0.5,
            marker=dict(colors=bar_colours, line=dict(color=BORDER, width=2)),
            textinfo="percent",
            textfont=dict(color=TEXT_PRIMARY, size=11),
            hovertemplate="%{label}<br>%{value:.1f} min<br>%{percent}<extra></extra>",
        ))
        fig_pie.update_layout(
            height=300,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT_SECONDARY, size=11),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_SECONDARY, size=10)),
            margin=dict(l=10, r=10, t=10, b=10),
            annotations=[dict(text=f"{total_journey:.0f}<br>min", x=0.5, y=0.5,
                              font=dict(size=20, color=TEXT_PRIMARY, weight=700),
                              showarrow=False)],
        )
        st.plotly_chart(fig_pie, key="journey_pie", width="stretch")


# === RENDER ===
if not compare_mode:
    _render_journey(selected_airport)
else:
    section_header("Cross-Airport Journey Comparison")

    comparison_data = []
    for code in AIRPORT_CODES:
        try:
            jdata = get_passenger_journey(demo_now, code)
            if jdata and jdata.get("total_journey_min"):
                comparison_data.append(jdata)
        except Exception:
            continue

    if not comparison_data:
        st.info("Journey data not available.")
    else:
        # Total journey comparison
        codes = [d["airport_code"] for d in comparison_data]
        totals = [d["total_journey_min"] for d in comparison_data]
        bottlenecks = [STAGE_LABELS.get(d.get("bottleneck", "?"), d.get("bottleneck", "?")) for d in comparison_data]
        bar_colors = [RED if t > 60 else YELLOW if t > 30 else GREEN for t in totals]

        fig_total = go.Figure(go.Bar(
            x=codes, y=totals,
            marker=dict(color=bar_colors, opacity=0.9, line=dict(color=BORDER, width=1)),
            text=[f"{t:.0f} min" for t in totals],
            textposition="outside", textfont=dict(color=TEXT_PRIMARY),
        ))
        apply_chart_theme(fig_total, title="Total Journey Time by Airport", height=350,
                          yaxis_title="Total Journey (min)")
        st.plotly_chart(fig_total, key="journey_total_compare", width="stretch")

        spacer(12)

        # Stacked bar by stage
        fig_stacked = go.Figure()
        stage_colors = [BLUE_PRIMARY, RED, YELLOW, GREEN, ORANGE]
        all_stage_names = []
        for d in comparison_data:
            for s in d.get("stages", []):
                sn = s["stage"]
                if sn not in all_stage_names:
                    all_stage_names.append(sn)

        for si, sn in enumerate(all_stage_names):
            vals = []
            for d in comparison_data:
                stage_match = next((s for s in d.get("stages", []) if s["stage"] == sn), None)
                vals.append(stage_match["avg_wait_min"] if stage_match else 0)
            fig_stacked.add_trace(go.Bar(
                name=STAGE_LABELS.get(sn, sn),
                x=codes, y=vals,
                marker=dict(color=stage_colors[si % len(stage_colors)], opacity=0.85),
            ))
        apply_chart_theme(fig_stacked, title="Journey Breakdown by Stage", height=400,
                          barmode="stack", yaxis_title="Wait (min)")
        st.plotly_chart(fig_stacked, key="journey_stacked", width="stretch")

        spacer(12)

        for d in comparison_data:
            bn = STAGE_LABELS.get(d.get("bottleneck", "?"), d.get("bottleneck", "?"))
            t = d["total_journey_min"]
            c = RED if t > 60 else YELLOW if t > 30 else GREEN
            st.markdown(
                f'<div style="color:{TEXT_SECONDARY};font-size:0.9em;margin-bottom:6px;">'
                f'<span style="color:{c};font-weight:700;">{d["airport_code"]}</span>: '
                f'{t:.0f} min total -- bottleneck at {bn}</div>',
                unsafe_allow_html=True,
            )
