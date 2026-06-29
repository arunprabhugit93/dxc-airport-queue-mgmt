"""Enterprise theme system with light/dark mode support."""

import streamlit as st


# ---------------------------------------------------------------------------
# Theme palettes
# ---------------------------------------------------------------------------
_DARK = {
    "bg": "#0E1117",
    "surface": "#1A1D23",
    "surface_hover": "#21252B",
    "border": "#2D3139",
    "border_accent": "#3D4451",
    "text_primary": "#FAFAFA",
    "text_secondary": "#8B949E",
    "text_muted": "#636B74",
    "sidebar_bg": "#161B22",
    "sidebar_border": "#2D3139",
}

_LIGHT = {
    "bg": "#FFFFFF",
    "surface": "#F6F8FA",
    "surface_hover": "#EEF1F5",
    "border": "#D0D7DE",
    "border_accent": "#B8C0CC",
    "text_primary": "#1F2328",
    "text_secondary": "#656D76",
    "text_muted": "#8B949E",
    "sidebar_bg": "#F6F8FA",
    "sidebar_border": "#D0D7DE",
}

# Status colors (shared across themes)
BLUE_PRIMARY = "#0080FF"
BLUE_LIGHT = "#58A6FF"
GREEN = "#2EA043"
YELLOW = "#D29922"
RED = "#F85149"
ORANGE = "#DB6D28"


def _get_mode() -> str:
    return st.session_state.get("theme_mode", "dark")


def _palette() -> dict:
    return _DARK if _get_mode() == "dark" else _LIGHT


# Dynamic color accessors
def _c(key: str) -> str:
    return _palette()[key]


# Convenience aliases (used by pages that import these)
@property
def _bg():
    return _c("bg")


# We expose module-level constants that pages import.
# These are the DARK defaults; inject_theme() applies the correct CSS at runtime.
# For HTML helpers, we read from session state dynamically.
BG = _DARK["bg"]
SURFACE = _DARK["surface"]
SURFACE_HOVER = _DARK["surface_hover"]
BORDER = _DARK["border"]
BORDER_ACCENT = _DARK["border_accent"]
TEXT_PRIMARY = _DARK["text_primary"]
TEXT_SECONDARY = _DARK["text_secondary"]
TEXT_MUTED = _DARK["text_muted"]


def t() -> dict:
    """Get current theme palette dict. Use t()['surface'] etc. for dynamic colors."""
    return _palette()


# ---------------------------------------------------------------------------
# Plotly chart theming
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
    """Apply the enterprise theme to any Plotly figure."""
    p = _palette()
    grid = p["border"]
    text = p["text_secondary"]
    title_color = p["text_primary"]

    layout = {
        "plot_bgcolor": "rgba(0,0,0,0)",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "margin": dict(l=40, r=20, t=50, b=40),
        "xaxis": dict(gridcolor=grid, linecolor=grid, zerolinecolor=grid),
        "yaxis": dict(gridcolor=grid, linecolor=grid, zerolinecolor=grid),
        "font": dict(color=text, size=12),
        "legend": dict(bgcolor="rgba(0,0,0,0)", font=dict(color=text)),
        "height": height,
    }
    if title:
        layout["title"] = dict(text=title, font=dict(color=title_color, size=16))
    layout.update(extra)
    fig.update_layout(**layout)


# ---------------------------------------------------------------------------
# CSS injection
# ---------------------------------------------------------------------------
def inject_theme() -> None:
    """Inject theme CSS. Call after set_page_config on every page."""
    if "theme_mode" not in st.session_state:
        st.session_state["theme_mode"] = "dark"

    p = _palette()
    mode = _get_mode()

    # Chart text colors for light mode
    chart_text = p["text_secondary"]

    st.markdown(f'''<style>
    .stApp {{ background-color: {p["bg"]}; }}

    /* Metric cards */
    [data-testid="stMetric"] {{
        background: {p["surface"]};
        border: 1px solid {p["border"]};
        border-radius: 8px;
        padding: 16px 20px;
    }}
    [data-testid="stMetricLabel"] {{
        color: {p["text_secondary"]} !important;
        font-size: 0.8em !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    [data-testid="stMetricValue"] {{
        color: {p["text_primary"]} !important;
        font-weight: 700 !important;
    }}

    /* Dataframes */
    [data-testid="stDataFrame"] {{
        border: 1px solid {p["border"]};
        border-radius: 8px;
    }}

    /* Buttons */
    .stButton > button {{
        background: {BLUE_PRIMARY};
        color: #FFFFFF;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        padding: 8px 24px;
        transition: all 0.2s ease;
    }}
    .stButton > button:hover {{
        background: #0066CC;
        transform: translateY(-1px);
    }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background: {p["sidebar_bg"]};
        border-right: 1px solid {p["sidebar_border"]};
    }}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
        color: {p["text_secondary"]};
    }}

    /* Sidebar navigation links */
    [data-testid="stSidebar"] a {{
        color: {p["text_secondary"]} !important;
        text-decoration: none;
        padding: 6px 12px;
        border-radius: 6px;
        display: block;
        transition: all 0.15s ease;
    }}
    [data-testid="stSidebar"] a:hover {{
        background: {p["surface_hover"]};
        color: {p["text_primary"]} !important;
    }}
    [data-testid="stSidebar"] a[aria-current="page"] {{
        background: {BLUE_PRIMARY}15;
        color: {BLUE_PRIMARY} !important;
        font-weight: 600;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{ gap: 4px; }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent;
        border-radius: 6px;
        padding: 8px 16px;
        color: {p["text_secondary"]};
    }}
    .stTabs [aria-selected="true"] {{
        background: {p["surface"]};
        color: {p["text_primary"]};
        border-bottom: 2px solid {BLUE_PRIMARY};
    }}

    /* Dividers */
    hr {{ border-color: {p["border"]} !important; }}

    /* Form labels */
    .stSelectbox label, .stSlider label, .stDateInput label, .stTimeInput label,
    .stNumberInput label, .stTextInput label {{
        color: {p["text_secondary"]} !important;
        font-size: 0.85em !important;
    }}

    /* Alert boxes */
    .stAlert {{ border-radius: 8px; }}

    /* Remove Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    /* Download button */
    .stDownloadButton > button {{
        background: transparent;
        border: 1px solid {p["border"]};
        color: {p["text_primary"]};
    }}
    .stDownloadButton > button:hover {{
        background: {p["surface"]};
        border-color: {BLUE_PRIMARY};
    }}

    /* Toggle / checkbox */
    .stCheckbox label span {{
        color: {p["text_secondary"]} !important;
    }}
    </style>''', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Reusable HTML component helpers (theme-aware)
# ---------------------------------------------------------------------------

def section_header(title: str) -> None:
    p = _palette()
    st.markdown(
        f'<h3 style="color:{p["text_primary"]};font-weight:600;margin:24px 0 12px 0;'
        f'padding-bottom:8px;border-bottom:1px solid {p["border"]};">{title}</h3>',
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, sublabel: str = "", border_color: str = "") -> str:
    p = _palette()
    border_left = f"border-left:4px solid {border_color};" if border_color else ""
    return (
        f'<div style="background:{p["surface"]};border:1px solid {p["border"]};{border_left}'
        f'border-radius:8px;padding:20px;">'
        f'<div style="font-size:0.8em;color:{p["text_secondary"]};text-transform:uppercase;'
        f'letter-spacing:0.05em;margin-bottom:8px;">{label}</div>'
        f'<div style="font-size:2em;font-weight:700;color:{p["text_primary"]};">{value}</div>'
        f'{f"""<div style="font-size:0.8em;color:{p["text_secondary"]};margin-top:4px;">{sublabel}</div>""" if sublabel else ""}'
        f'</div>'
    )


def status_badge(status: str) -> str:
    colors = {"OK": GREEN, "WARNING": YELLOW, "BREACH": RED}
    c = colors.get(status, "#636B74")
    return (
        f'<span style="background:{c};color:#fff;padding:3px 10px;border-radius:4px;'
        f'font-size:0.75em;font-weight:600;letter-spacing:0.03em;">{status}</span>'
    )


def severity_badge(severity: str) -> str:
    colors = {"LOW": "#636B74", "MEDIUM": YELLOW, "HIGH": RED}
    c = colors.get(severity, "#636B74")
    return (
        f'<span style="background:{c};color:#fff;padding:3px 10px;border-radius:4px;'
        f'font-size:0.75em;font-weight:600;letter-spacing:0.03em;">{severity}</span>'
    )


def priority_badge(priority: str) -> str:
    colors = {"HIGH": RED, "MEDIUM": YELLOW, "LOW": GREEN}
    c = colors.get(priority.upper(), "#636B74")
    return (
        f'<span style="background:{c};color:#fff;padding:3px 10px;border-radius:4px;'
        f'font-size:0.75em;font-weight:600;letter-spacing:0.03em;">{priority}</span>'
    )


def trend_arrow(trend: str) -> str:
    if trend == "UP":
        return f'<span style="color:{RED};font-weight:700;">&#9650; UP</span>'
    if trend == "DOWN":
        return f'<span style="color:{GREEN};font-weight:700;">&#9660; DOWN</span>'
    p = _palette()
    return f'<span style="color:{p["text_muted"]};font-weight:700;">&#9654; FLAT</span>'


def spacer(height: int = 24) -> None:
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
    import plotly.graph_objects as go
    p = _palette()

    if threshold_val is None:
        threshold_val = warn_threshold

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title=dict(text=label, font=dict(size=14, color=p["text_secondary"])),
        number=dict(font=dict(size=28, color=p["text_primary"]), suffix=suffix),
        gauge=dict(
            axis=dict(range=[0, max_val], tickcolor=p["text_muted"]),
            bar=dict(color=BLUE_PRIMARY),
            bgcolor=p["surface"],
            bordercolor=p["border"],
            steps=[
                dict(range=[0, good_threshold], color="rgba(46,160,67,0.2)"),
                dict(range=[good_threshold, warn_threshold], color="rgba(210,153,34,0.2)"),
                dict(range=[warn_threshold, max_val], color="rgba(248,81,73,0.2)"),
            ],
            threshold=dict(
                line=dict(color=RED, width=2),
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
