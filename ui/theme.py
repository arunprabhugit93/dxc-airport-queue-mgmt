"""Enterprise dark theme injection for Streamlit dashboard."""

import streamlit as st


# ---------------------------------------------------------------------------
# Design system color constants
# ---------------------------------------------------------------------------
BG = "#0E1117"
SURFACE = "#1A1D23"
SURFACE_HOVER = "#21252B"
BORDER = "#2D3139"
BORDER_ACCENT = "#3D4451"

TEXT_PRIMARY = "#FAFAFA"
TEXT_SECONDARY = "#8B949E"
TEXT_MUTED = "#636B74"

BLUE_PRIMARY = "#0080FF"
BLUE_LIGHT = "#58A6FF"
GREEN = "#2EA043"
YELLOW = "#D29922"
RED = "#F85149"
ORANGE = "#DB6D28"


# ---------------------------------------------------------------------------
# Plotly layout template (apply to every chart)
# ---------------------------------------------------------------------------
PLOTLY_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=40, r=20, t=50, b=40),
)

PLOTLY_AXES = dict(
    xaxis=dict(gridcolor="#2D3139", linecolor="#2D3139", zerolinecolor="#2D3139"),
    yaxis=dict(gridcolor="#2D3139", linecolor="#2D3139", zerolinecolor="#2D3139"),
)

PLOTLY_FONT = dict(color="#8B949E", size=12)
PLOTLY_TITLE_FONT = dict(color="#FAFAFA", size=16)
PLOTLY_LEGEND = dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8B949E"))


def apply_chart_theme(fig, title: str = "", height: int = 400, **extra) -> None:
    """Apply the enterprise dark theme to any Plotly figure."""
    layout = {
        **PLOTLY_LAYOUT,
        **PLOTLY_AXES,
        "font": PLOTLY_FONT,
        "legend": PLOTLY_LEGEND,
        "height": height,
    }
    if title:
        layout["title"] = dict(text=title, font=PLOTLY_TITLE_FONT)
    layout.update(extra)
    fig.update_layout(**layout)


def inject_theme() -> None:
    """Inject enterprise dark-mode CSS overrides. Call after set_page_config."""
    st.markdown('''<style>
    /* Enterprise dark theme overrides */
    .stApp { background-color: #0E1117; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: #1A1D23;
        border: 1px solid #2D3139;
        border-radius: 8px;
        padding: 16px 20px;
    }
    [data-testid="stMetricLabel"] {
        color: #8B949E !important;
        font-size: 0.8em !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    [data-testid="stMetricValue"] {
        color: #FAFAFA !important;
        font-weight: 700 !important;
    }

    /* Dataframes */
    [data-testid="stDataFrame"] {
        border: 1px solid #2D3139;
        border-radius: 8px;
    }

    /* Buttons */
    .stButton > button {
        background: #0080FF;
        color: #FAFAFA;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        padding: 8px 24px;
        transition: background 0.2s ease;
    }
    .stButton > button:hover {
        background: #0066CC;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #161B22;
        border-right: 1px solid #2D3139;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 6px;
        padding: 8px 16px;
        color: #8B949E;
    }
    .stTabs [aria-selected="true"] {
        background: #1A1D23;
        color: #FAFAFA;
        border-bottom: 2px solid #0080FF;
    }

    /* Dividers */
    hr { border-color: #2D3139 !important; }

    /* Selectbox, slider, input styling */
    .stSelectbox label, .stSlider label, .stDateInput label, .stTimeInput label {
        color: #8B949E !important;
        font-size: 0.85em !important;
    }

    /* Alert boxes */
    .stAlert { border-radius: 8px; }

    /* Remove Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>''', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Reusable HTML component helpers
# ---------------------------------------------------------------------------

def section_header(title: str) -> None:
    """Render a styled section header with bottom border."""
    st.markdown(
        f'<h3 style="color:#FAFAFA;font-weight:600;margin:24px 0 12px 0;'
        f'padding-bottom:8px;border-bottom:1px solid #2D3139;">{title}</h3>',
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, sublabel: str = "", border_color: str = "") -> str:
    """Return HTML for a single metric card."""
    border_left = f"border-left:4px solid {border_color};" if border_color else ""
    return (
        f'<div style="background:#1A1D23;border:1px solid #2D3139;{border_left}'
        f'border-radius:8px;padding:20px;">'
        f'<div style="font-size:0.8em;color:#8B949E;text-transform:uppercase;'
        f'letter-spacing:0.05em;margin-bottom:8px;">{label}</div>'
        f'<div style="font-size:2em;font-weight:700;color:#FAFAFA;">{value}</div>'
        f'{f"""<div style="font-size:0.8em;color:#8B949E;margin-top:4px;">{sublabel}</div>""" if sublabel else ""}'
        f'</div>'
    )


def status_badge(status: str) -> str:
    """Return an HTML badge span for an SLA status value."""
    colors = {"OK": "#2EA043", "WARNING": "#D29922", "BREACH": "#F85149"}
    c = colors.get(status, "#636B74")
    return (
        f'<span style="background:{c};color:#fff;padding:3px 10px;border-radius:4px;'
        f'font-size:0.75em;font-weight:600;letter-spacing:0.03em;">{status}</span>'
    )


def severity_badge(severity: str) -> str:
    """Return an HTML badge for a severity value."""
    colors = {"LOW": "#636B74", "MEDIUM": "#D29922", "HIGH": "#F85149"}
    c = colors.get(severity, "#636B74")
    return (
        f'<span style="background:{c};color:#fff;padding:3px 10px;border-radius:4px;'
        f'font-size:0.75em;font-weight:600;letter-spacing:0.03em;">{severity}</span>'
    )


def priority_badge(priority: str) -> str:
    """Return an HTML badge for recommendation priority."""
    colors = {"HIGH": "#F85149", "MEDIUM": "#D29922", "LOW": "#2EA043"}
    c = colors.get(priority.upper(), "#636B74")
    return (
        f'<span style="background:{c};color:#fff;padding:3px 10px;border-radius:4px;'
        f'font-size:0.75em;font-weight:600;letter-spacing:0.03em;">{priority}</span>'
    )


def trend_arrow(trend: str) -> str:
    """Return a coloured trend arrow string."""
    if trend == "UP":
        return f'<span style="color:{RED};font-weight:700;">&#9650; UP</span>'
    if trend == "DOWN":
        return f'<span style="color:{GREEN};font-weight:700;">&#9660; DOWN</span>'
    return f'<span style="color:{TEXT_MUTED};font-weight:700;">&#9654; FLAT</span>'


def spacer(height: int = 24) -> None:
    """Insert vertical spacing between sections."""
    st.markdown(f'<div style="height:{height}px;"></div>', unsafe_allow_html=True)


def gauge_figure(
    value: float,
    label: str,
    max_val: float = 30,
    good_threshold: float = 7,
    warn_threshold: float = 10,
    suffix: str = "",
    threshold_val: float | None = None,
):
    """Return a dark-themed go.Indicator gauge figure."""
    import plotly.graph_objects as go

    if threshold_val is None:
        threshold_val = warn_threshold

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title=dict(text=label, font=dict(size=14, color="#8B949E")),
        number=dict(font=dict(size=28, color="#FAFAFA"), suffix=suffix),
        gauge=dict(
            axis=dict(range=[0, max_val], tickcolor="#636B74"),
            bar=dict(color="#0080FF"),
            bgcolor="#1A1D23",
            bordercolor="#2D3139",
            steps=[
                dict(range=[0, good_threshold], color="rgba(46,160,67,0.2)"),
                dict(range=[good_threshold, warn_threshold], color="rgba(210,153,34,0.2)"),
                dict(range=[warn_threshold, max_val], color="rgba(248,81,73,0.2)"),
            ],
            threshold=dict(
                line=dict(color="#F85149", width=2),
                thickness=0.8,
                value=threshold_val,
            ),
        ),
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=50, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
