# -*- coding: utf-8 -*-
"""
CGB TERMINAL — XAU/USD
Professional Streamlit market-analysis terminal.

The application keeps the original analytical engines:
- Gold / DXY / US 2Y market data
- Quantitative bias score
- Technical analysis
- COT positioning
- ETF options open-interest walls
- Risk calculator
- News flow classification

The interface is rebuilt as an institutional-style terminal:
- No decorative emojis
- Persistent left navigation
- Professional themes
- Configurable support/resistance levels
- Clear data-status indicators
- Responsive cards and charts
"""

import os
import base64
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
import yfinance as yf

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except Exception:
    HAS_CURL_CFFI = False

try:
    import feedparser
    HAS_FEEDPARSER = True
except Exception:
    HAS_FEEDPARSER = False


# ---------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="CGB Terminal | XAU/USD",
    page_icon="logo.jpg" if os.path.exists("logo.jpg") else "📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------
# PROFESSIONAL THEMES
# ---------------------------------------------------------------------
THEMES = {
    "Institutional Dark": {
        "bg": "#0b0f14",
        "panel": "#111720",
        "panel_2": "#151c26",
        "border": "#27313d",
        "text": "#edf2f7",
        "muted": "#8d9aaa",
        "primary": "#d8a84e",
        "primary_2": "#f1c66a",
        "bull": "#2ac58b",
        "bear": "#ef6262",
        "neutral": "#d8a84e",
        "blue": "#5da9e9",
        "grid": "#202a35",
    },
    "Obsidian Gold": {
        "bg": "#090909",
        "panel": "#12110e",
        "panel_2": "#191711",
        "border": "#3b3423",
        "text": "#f5f2e9",
        "muted": "#a69f8c",
        "primary": "#c9a227",
        "primary_2": "#e7c85b",
        "bull": "#36c98f",
        "bear": "#ef6666",
        "neutral": "#d4ad38",
        "blue": "#5ca8df",
        "grid": "#2b271c",
    },
    "Executive Light": {
        "bg": "#f3f5f8",
        "panel": "#ffffff",
        "panel_2": "#f8fafc",
        "border": "#d8dee7",
        "text": "#17202b",
        "muted": "#667384",
        "primary": "#9a6a16",
        "primary_2": "#b88323",
        "bull": "#16865e",
        "bear": "#c64242",
        "neutral": "#9a6a16",
        "blue": "#256aa8",
        "grid": "#dfe5ec",
    },
    "Slate Blue": {
        "bg": "#0c121c",
        "panel": "#121a27",
        "panel_2": "#172233",
        "border": "#2a3a4e",
        "text": "#e9eef5",
        "muted": "#8c9aae",
        "primary": "#6ea8df",
        "primary_2": "#8fc0ef",
        "bull": "#35c18b",
        "bear": "#eb6565",
        "neutral": "#d5a84d",
        "blue": "#6ea8df",
        "grid": "#233246",
    },
}


# ---------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------
if "theme" not in st.session_state:
    st.session_state.theme = "Institutional Dark"
if "module" not in st.session_state:
    st.session_state.module = "Overview"


T = THEMES[st.session_state.theme]


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------
def get_logo_data_uri():
    candidates = ["logo.jpg", "logo.jpeg", "logo.png", "assets/logo.jpg", "assets/logo.png"]
    for path in candidates:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            ext = path.rsplit(".", 1)[-1].lower()
            mime = "image/jpeg" if ext in {"jpg", "jpeg"} else "image/png"
            with open(path, "rb") as f:
                return f"data:{mime};base64,{base64.b64encode(f.read()).decode('utf-8')}"
    return ""


LOGO_SRC = get_logo_data_uri()


def safe_float(value, default=np.nan):
    try:
        return float(value)
    except Exception:
        return default


def fmt_money(value, decimals=2):
    if value is None or pd.isna(value):
        return "—"
    return f"${value:,.{decimals}f}"


def fmt_num(value, decimals=2):
    if value is None or pd.isna(value):
        return "—"
    return f"{value:,.{decimals}f}"


def pct_change(series, periods=1):
    if series is None or len(series) <= periods:
        return np.nan
    return (series.iloc[-1] / series.iloc[-1 - periods] - 1) * 100


def status_badge(text, kind="neutral"):
    cls = {
        "bull": "badge badge-bull",
        "bear": "badge badge-bear",
        "neutral": "badge badge-neutral",
        "info": "badge badge-info",
    }.get(kind, "badge badge-neutral")
    return f'<span class="{cls}">{text}</span>'


# ---------------------------------------------------------------------
# GLOBAL CSS
# ---------------------------------------------------------------------
logo_watermark = ""
if LOGO_SRC:
    logo_watermark = f"""
    .stApp::before {{
        content: "";
        position: fixed;
        inset: 0;
        background-image: url("{LOGO_SRC}");
        background-repeat: no-repeat;
        background-position: 52% 54%;
        background-size: 520px;
        opacity: 0.018;
        pointer-events: none;
        z-index: 0;
    }}
    """

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');

    :root {{
        --bg: {T['bg']};
        --panel: {T['panel']};
        --panel2: {T['panel_2']};
        --border: {T['border']};
        --text: {T['text']};
        --muted: {T['muted']};
        --primary: {T['primary']};
        --primary2: {T['primary_2']};
        --bull: {T['bull']};
        --bear: {T['bear']};
        --neutral: {T['neutral']};
        --blue: {T['blue']};
        --grid: {T['grid']};
    }}

    html, body, [class*="css"] {{
        font-family: Inter, sans-serif;
    }}

    .stApp {{
        background: var(--bg);
        color: var(--text);
    }}

    {logo_watermark}

    #MainMenu, footer, header {{
        visibility: hidden;
    }}

    .block-container {{
        max-width: 1680px;
        padding-top: 1.4rem;
        padding-bottom: 3rem;
        position: relative;
        z-index: 1;
    }}

    section[data-testid="stSidebar"] {{
        background: var(--panel);
        border-right: 1px solid var(--border);
    }}

    section[data-testid="stSidebar"] > div {{
        padding-top: 1.2rem;
    }}

    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] label {{
        color: var(--text);
    }}

    .sidebar-brand {{
        display:flex;
        align-items:center;
        gap:12px;
        padding: 4px 4px 20px 4px;
        border-bottom:1px solid var(--border);
        margin-bottom:18px;
    }}

    .brand-mark {{
        width:42px;
        height:42px;
        border-radius:10px;
        display:flex;
        align-items:center;
        justify-content:center;
        overflow:hidden;
        background:linear-gradient(145deg, var(--primary), var(--primary2));
        color:#111;
        font-weight:800;
        letter-spacing:-0.04em;
    }}

    .brand-mark img {{
        width:100%;
        height:100%;
        object-fit:cover;
    }}

    .brand-name {{
        font-size:0.98rem;
        font-weight:800;
        letter-spacing:-0.02em;
        color:var(--text);
        line-height:1.1;
    }}

    .brand-sub {{
        color:var(--muted);
        font-size:0.68rem;
        margin-top:4px;
        letter-spacing:.08em;
        text-transform:uppercase;
    }}

    .side-section {{
        color:var(--muted);
        font-size:0.67rem;
        font-weight:800;
        letter-spacing:.12em;
        text-transform:uppercase;
        margin:18px 0 8px;
    }}

    .terminal-header {{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:20px;
        padding:18px 20px;
        background:linear-gradient(135deg, var(--panel) 0%, var(--panel2) 100%);
        border:1px solid var(--border);
        border-radius:14px;
        box-shadow:0 12px 34px rgba(0,0,0,.16);
        margin-bottom:16px;
    }}

    .header-left {{
        display:flex;
        align-items:center;
        gap:14px;
        min-width:0;
    }}

    .header-logo {{
        width:48px;
        height:48px;
        border-radius:10px;
        object-fit:cover;
        border:1px solid var(--border);
        flex-shrink:0;
    }}

    .header-logo-fallback {{
        width:48px;
        height:48px;
        border-radius:10px;
        background:linear-gradient(145deg,var(--primary),var(--primary2));
        color:#111;
        display:flex;
        align-items:center;
        justify-content:center;
        font-weight:900;
        flex-shrink:0;
    }}

    .eyebrow {{
        color:var(--primary2);
        font-size:.68rem;
        font-weight:800;
        letter-spacing:.12em;
        text-transform:uppercase;
        margin-bottom:3px;
    }}

    .terminal-title {{
        font-size:1.45rem;
        line-height:1.1;
        font-weight:800;
        letter-spacing:-.035em;
        margin:0;
        color:var(--text);
    }}

    .terminal-subtitle {{
        margin-top:5px;
        color:var(--muted);
        font-size:.78rem;
    }}

    .header-status {{
        display:flex;
        align-items:center;
        gap:8px;
        white-space:nowrap;
    }}

    .live-dot {{
        width:7px;
        height:7px;
        border-radius:50%;
        background:var(--bull);
        box-shadow:0 0 0 4px rgba(42,197,139,.10);
    }}

    .status-text {{
        color:var(--muted);
        font-size:.72rem;
        font-weight:700;
        letter-spacing:.06em;
        text-transform:uppercase;
    }}

    .section-head {{
        display:flex;
        align-items:end;
        justify-content:space-between;
        gap:12px;
        margin:20px 0 10px;
    }}

    .section-title {{
        font-size:1.05rem;
        font-weight:800;
        letter-spacing:-.02em;
        color:var(--text);
    }}

    .section-desc {{
        color:var(--muted);
        font-size:.76rem;
        margin-top:3px;
    }}

    .panel {{
        background:var(--panel);
        border:1px solid var(--border);
        border-radius:13px;
        padding:16px;
        box-shadow:0 8px 24px rgba(0,0,0,.10);
    }}

    .panel-tight {{
        padding:13px 15px;
    }}

    .metric-card {{
        background:var(--panel);
        border:1px solid var(--border);
        border-radius:12px;
        padding:14px 15px;
        min-height:94px;
    }}

    .metric-label {{
        color:var(--muted);
        font-size:.68rem;
        font-weight:800;
        text-transform:uppercase;
        letter-spacing:.09em;
    }}

    .metric-value {{
        font-family:'JetBrains Mono', monospace;
        font-size:1.3rem;
        font-weight:700;
        color:var(--text);
        margin-top:7px;
        letter-spacing:-.02em;
    }}

    .metric-sub {{
        font-size:.70rem;
        color:var(--muted);
        margin-top:5px;
    }}

    .metric-positive {{ color:var(--bull) !important; }}
    .metric-negative {{ color:var(--bear) !important; }}
    .metric-neutral {{ color:var(--neutral) !important; }}

    .score-panel {{
        background:linear-gradient(145deg,var(--panel),var(--panel2));
        border:1px solid var(--border);
        border-radius:14px;
        padding:12px;
    }}

    .score-caption {{
        text-align:center;
        color:var(--muted);
        font-size:.68rem;
        font-weight:800;
        text-transform:uppercase;
        letter-spacing:.10em;
    }}

    .score-value {{
        text-align:center;
        font-family:'JetBrains Mono',monospace;
        font-size:2.15rem;
        font-weight:700;
        margin-top:-8px;
    }}

    .score-state {{
        text-align:center;
        font-size:.86rem;
        font-weight:800;
        letter-spacing:.05em;
        text-transform:uppercase;
        margin-top:-4px;
    }}

    .badge {{
        display:inline-flex;
        align-items:center;
        border-radius:999px;
        padding:4px 8px;
        font-size:.61rem;
        font-weight:800;
        letter-spacing:.08em;
        text-transform:uppercase;
        border:1px solid transparent;
    }}

    .badge-bull {{ color:var(--bull); background:rgba(42,197,139,.10); border-color:rgba(42,197,139,.25); }}
    .badge-bear {{ color:var(--bear); background:rgba(239,98,98,.10); border-color:rgba(239,98,98,.25); }}
    .badge-neutral {{ color:var(--neutral); background:rgba(216,168,78,.10); border-color:rgba(216,168,78,.25); }}
    .badge-info {{ color:var(--blue); background:rgba(93,169,233,.10); border-color:rgba(93,169,233,.25); }}

    .data-row {{
        display:grid;
        grid-template-columns: 1fr auto;
        gap:12px;
        padding:9px 0;
        border-bottom:1px solid var(--border);
        font-size:.77rem;
    }}

    .data-row:last-child {{ border-bottom:none; }}
    .data-key {{ color:var(--muted); }}
    .data-value {{ color:var(--text); font-family:'JetBrains Mono',monospace; font-weight:600; }}

    .level-table {{
        width:100%;
        border-collapse:collapse;
        font-size:.75rem;
    }}

    .level-table th {{
        color:var(--muted);
        font-size:.62rem;
        text-transform:uppercase;
        letter-spacing:.08em;
        text-align:left;
        padding:8px 10px;
        border-bottom:1px solid var(--border);
    }}

    .level-table td {{
        padding:9px 10px;
        border-bottom:1px solid var(--border);
        color:var(--text);
    }}

    .level-table tr:last-child td {{ border-bottom:none; }}

    .price-cell {{
        font-family:'JetBrains Mono',monospace;
        font-weight:700;
    }}

    .signal-box {{
        border:1px solid var(--border);
        background:linear-gradient(135deg,var(--panel),var(--panel2));
        border-radius:13px;
        padding:15px 16px;
        margin-bottom:14px;
    }}

    .signal-kicker {{
        color:var(--primary2);
        font-size:.64rem;
        font-weight:800;
        letter-spacing:.11em;
        text-transform:uppercase;
    }}

    .signal-title {{
        font-size:.98rem;
        font-weight:800;
        margin:5px 0 5px;
        color:var(--text);
    }}

    .signal-text {{
        font-size:.76rem;
        color:var(--muted);
        line-height:1.55;
        margin:0;
    }}

    .news-card {{
        background:var(--panel);
        border:1px solid var(--border);
        border-radius:11px;
        padding:13px 14px;
        margin-bottom:9px;
        transition:border-color .18s ease, transform .18s ease;
    }}

    .news-card:hover {{
        border-color:var(--primary);
        transform:translateY(-1px);
    }}

    .news-top {{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        margin-bottom:7px;
    }}

    .news-time {{
        color:var(--muted);
        font-size:.66rem;
        white-space:nowrap;
    }}

    .news-link {{
        color:var(--text) !important;
        text-decoration:none !important;
        font-size:.78rem;
        line-height:1.45;
        font-weight:650;
    }}

    .cot-card {{
        background:var(--panel);
        border:1px solid var(--border);
        border-radius:12px;
        padding:14px;
        height:100%;
    }}

    .cot-title {{
        color:var(--text);
        font-size:.75rem;
        font-weight:800;
        margin-bottom:8px;
    }}

    .cot-net {{
        font-family:'JetBrains Mono',monospace;
        font-size:1.1rem;
        font-weight:700;
        margin:7px 0 10px;
    }}

    .footer {{
        border-top:1px solid var(--border);
        margin-top:30px;
        padding:18px 0 0;
        color:var(--muted);
        font-size:.66rem;
        line-height:1.5;
        text-align:center;
    }}

    div[data-testid="stMetric"] {{
        background:var(--panel) !important;
        border:1px solid var(--border) !important;
        border-radius:12px !important;
        padding:12px 14px !important;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap:2px;
        border-bottom:1px solid var(--border);
    }}

    .stTabs [data-baseweb="tab"] {{
        color:var(--muted);
        font-weight:700;
        font-size:.74rem;
        padding:9px 13px;
    }}

    .stTabs [aria-selected="true"] {{
        color:var(--primary2) !important;
        border-bottom:2px solid var(--primary);
    }}

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div {{
        background:var(--panel2);
        border-color:var(--border);
    }}

    .stButton > button {{
        border:1px solid var(--border);
        background:var(--panel2);
        color:var(--text);
        border-radius:9px;
        font-weight:700;
        transition:all .18s ease;
    }}

    .stButton > button:hover {{
        border-color:var(--primary);
        color:var(--primary2);
    }}

    .stRadio label {{
        font-size:.78rem !important;
    }}

    @media (max-width: 900px) {{
        .terminal-header {{
            align-items:flex-start;
            flex-direction:column;
        }}
        .header-status {{
            align-self:flex-start;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------
# SIDEBAR / NAVIGATION
# ---------------------------------------------------------------------
with st.sidebar:
    logo_html = (
        f'<div class="brand-mark"><img src="{LOGO_SRC}" alt="CGB"></div>'
        if LOGO_SRC
        else '<div class="brand-mark">CGB</div>'
    )
    st.markdown(
        f"""
        <div class="sidebar-brand">
            {logo_html}
            <div>
                <div class="brand-name">CGB TERMINAL</div>
                <div class="brand-sub">XAU/USD Research Desk</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="side-section">Terminal</div>', unsafe_allow_html=True)
    modules = [
        "Overview",
        "Gold Analysis",
        "Macro & Correlation",
        "COT Positioning",
        "Options Structure",
        "Risk Management",
        "News Flow",
    ]
    st.session_state.module = st.radio(
        "Módulo",
        modules,
        index=modules.index(st.session_state.module),
        label_visibility="collapsed",
    )

    st.markdown('<div class="side-section">Interface</div>', unsafe_allow_html=True)
    selected_theme = st.selectbox(
        "Tema visual",
        list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.theme),
        label_visibility="collapsed",
    )
    if selected_theme != st.session_state.theme:
        st.session_state.theme = selected_theme
        st.rerun()

    st.markdown('<div class="side-section">Market data</div>', unsafe_allow_html=True)
    period_choice = st.selectbox(
        "Ventana de gráficos",
        ["3mo", "6mo", "1y", "2y"],
        index=2,
    )

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        support_count = st.number_input(
            "Soportes",
            min_value=1,
            max_value=4,
            value=2,
            step=1,
        )
    with col_s2:
        resistance_count = st.number_input(
            "Resistencias",
            min_value=1,
            max_value=4,
            value=2,
            step=1,
        )

    show_volume = st.toggle("Mostrar volumen", value=True)
    auto_refresh = st.toggle("Actualizar al abrir", value=False)

    st.markdown('<div class="side-section">Actions</div>', unsafe_allow_html=True)
    if st.button("Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown(
        f"""
        <div style="margin-top:18px;padding-top:14px;border-top:1px solid {T['border']};">
            <div style="font-size:.65rem;color:{T['muted']};line-height:1.55;">
                CGB Terminal<br>
                Datos informativos y educativos.<br>
                No constituye asesoramiento financiero.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------
# DATA ACCESS
# ---------------------------------------------------------------------
# NOTE:
# The first version relied almost entirely on yfinance. On some Streamlit
# Cloud deployments yfinance can return an empty DataFrame because Yahoo
# blocks/changes the session handshake.  We therefore use a direct chart
# request as the PRIMARY historical-price source and keep yfinance only as
# a secondary fallback.

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/139 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
}

DATA_ERRORS = {}


def remember_error(source, message):
    DATA_ERRORS[source] = str(message)[-300:]


def get_yf_session():
    if HAS_CURL_CFFI:
        try:
            return curl_requests.Session(impersonate="chrome")
        except Exception:
            return None
    return None


YF_SESSION = get_yf_session()


def retry(fn, tries=2, delay=1.0):
    last = None
    for attempt in range(tries):
        try:
            result = fn()
            if result is not None and not (
                isinstance(result, pd.DataFrame) and result.empty
            ):
                return result
        except Exception as exc:
            last = exc
            if attempt + 1 < tries:
                time.sleep(delay)
    if last:
        return None
    return None


def _yahoo_chart_request(ticker, period="1y", interval="1d"):
    """Fetch OHLCV from Yahoo's chart endpoint without yfinance."""
    last_error = None
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            url = f"https://{host}/v8/finance/chart/{ticker}"
            response = requests.get(
                url,
                params={
                    "range": period,
                    "interval": interval,
                    "includePrePost": "false",
                    "events": "div,splits",
                },
                headers=HTTP_HEADERS,
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            result = ((payload.get("chart") or {}).get("result") or [None])[0]
            if not result:
                err = ((payload.get("chart") or {}).get("error") or {}).get("description")
                raise RuntimeError(err or "Yahoo returned no chart result")

            timestamps = result.get("timestamp") or []
            quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
            if not timestamps or not quote:
                raise RuntimeError("Yahoo chart contains no OHLCV rows")

            frame = pd.DataFrame({
                "Open": quote.get("open", []),
                "High": quote.get("high", []),
                "Low": quote.get("low", []),
                "Close": quote.get("close", []),
                "Volume": quote.get("volume", []),
            }, index=pd.to_datetime(timestamps, unit="s", utc=True))
            frame.index.name = "Datetime"
            frame = frame.apply(pd.to_numeric, errors="coerce")
            frame = frame.dropna(subset=["Close"])
            if frame.empty:
                raise RuntimeError("Yahoo returned only empty price rows")
            return frame
        except Exception as exc:
            last_error = exc

    raise RuntimeError(last_error or "Yahoo chart request failed")


@st.cache_data(ttl=300, show_spinner=False)
def get_price_data(ticker: str, period="1y", interval="1d"):
    # Primary: direct Yahoo chart request.
    try:
        return _yahoo_chart_request(ticker, period=period, interval=interval)
    except Exception as exc:
        remember_error(f"Yahoo {ticker}", exc)

    # Secondary: yfinance.
    try:
        tk = yf.Ticker(ticker, session=YF_SESSION) if YF_SESSION else yf.Ticker(ticker)
        df = tk.history(period=period, interval=interval, auto_adjust=False)
        if df is not None and not df.empty and "Close" in df.columns:
            df = df.dropna(subset=["Close"])
            if not df.empty:
                return df
    except Exception as exc:
        remember_error(f"yfinance {ticker}", exc)

    return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=False)
def get_us02y():
    # FRED's public CSV endpoint does not require an API key.
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2"
        r = requests.get(url, headers=HTTP_HEADERS, timeout=15)
        r.raise_for_status()
        from io import StringIO
        df = pd.read_csv(StringIO(r.text))
        df.columns = ["Date", "Close"]
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df = df.dropna(subset=["Date", "Close"]).set_index("Date")
        if not df.empty:
            return df.tail(500)
    except Exception as exc:
        remember_error("FRED DGS2", exc)

    # Fallback: Yahoo 2-year Treasury future.
    try:
        df = get_price_data("2YY=F", period="1y")
        if not df.empty:
            return df[["Close"]]
    except Exception as exc:
        remember_error("Yahoo 2YY=F", exc)

    return pd.DataFrame()


@st.cache_data(ttl=1800, show_spinner=False)
def get_cot_gold():
    url_disagg = "https://publicreporting.cftc.gov/resource/kh3c-5v3d.json"
    url_legacy = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
    params = {
        "$where": "cftc_contract_market_code='088691'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": 30,
    }

    for url in (url_disagg, url_legacy):
        try:
            r = requests.get(url, params=params, timeout=15, headers=HTTP_HEADERS)
            r.raise_for_status()
            rows = r.json()
            if not rows:
                continue
            df = pd.DataFrame(rows)
            for col in df.columns:
                if "positions" in col or "pct_of_oi" in col or col == "open_interest_all":
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            df["report_date_as_yyyy_mm_dd"] = pd.to_datetime(
                df["report_date_as_yyyy_mm_dd"], errors="coerce"
            )
            return df.sort_values("report_date_as_yyyy_mm_dd")
        except Exception as exc:
            remember_error("CFTC COT", exc)

    return pd.DataFrame()


@st.cache_data(ttl=1800, show_spinner=False)
def get_options_walls(tickers=("GLD", "IAU")):
    for ticker in tickers:
        try:
            tk = yf.Ticker(ticker, session=YF_SESSION) if YF_SESSION else yf.Ticker(ticker)
            exps = tk.options
            if not exps:
                continue
            hist = tk.history(period="5d")
            if hist.empty:
                continue
            spot_price = hist["Close"].iloc[-1]
            for exp in exps[:3]:
                chain = tk.option_chain(exp)
                calls = chain.calls.dropna(subset=["strike", "openInterest"])
                puts = chain.puts.dropna(subset=["strike", "openInterest"])
                calls_f = calls[(calls["strike"] >= spot_price * .88) & (calls["strike"] <= spot_price * 1.12)]
                puts_f = puts[(puts["strike"] >= spot_price * .88) & (puts["strike"] <= spot_price * 1.12)]
                c_agg = calls_f.groupby("strike")["openInterest"].sum().reset_index()
                p_agg = puts_f.groupby("strike")["openInterest"].sum().reset_index()
                if c_agg["openInterest"].sum() > 0 or p_agg["openInterest"].sum() > 0:
                    return c_agg, p_agg, exp, ticker, spot_price
        except Exception as exc:
            remember_error(f"Options {ticker}", exc)
    return pd.DataFrame(), pd.DataFrame(), None, None, None


# ---------------------------------------------------------------------
# TECHNICAL ENGINE
# ---------------------------------------------------------------------
def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(df, period=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def bollinger_bands(series, window=20, num_sd=2):
    sma = series.rolling(window).mean()
    std = series.rolling(window).std()
    return sma + std * num_sd, sma, sma - std * num_sd


def pivot_table(df):
    if len(df) < 2:
        return pd.DataFrame(), 0.0

    last = df.iloc[-2]
    current = float(df.iloc[-1]["Close"])
    h, l, c = float(last["High"]), float(last["Low"]), float(last["Close"])

    pp = (h + l + c) / 3
    r1, s1 = 2 * pp - l, 2 * pp - h
    r2, s2 = pp + (h - l), pp - (h - l)
    r3, s3 = h + 2 * (pp - l), l - 2 * (h - pp)

    rng = h - l
    r4 = c + rng * 1.1 / 2
    s4 = c - rng * 1.1 / 2

    rows = [
        ("R4 · Camarilla breakout", r4, "Resistance"),
        ("R3", r3, "Resistance"),
        ("R2", r2, "Resistance"),
        ("R1", r1, "Resistance"),
        ("PP · Pivot", pp, "Pivot"),
        ("S1", s1, "Support"),
        ("S2", s2, "Support"),
        ("S3", s3, "Support"),
        ("S4 · Camarilla breakout", s4, "Support"),
    ]

    dfp = pd.DataFrame(rows, columns=["Level", "Price", "Type"])
    dfp["Distance"] = dfp["Price"] - current
    return dfp.sort_values("Price", ascending=False), current


def selected_levels(dfp, ref_price, support_n, resistance_n):
    if dfp.empty:
        return dfp

    resistances = dfp[
        (dfp["Type"] == "Resistance") & (dfp["Price"] > ref_price)
    ].sort_values("Price")
    supports = dfp[
        (dfp["Type"] == "Support") & (dfp["Price"] < ref_price)
    ].sort_values("Price", ascending=False)
    pivot = dfp[dfp["Type"] == "Pivot"]

    selected = pd.concat(
        [
            resistances.head(resistance_n),
            pivot,
            supports.head(support_n),
        ]
    )
    return selected.sort_values("Price", ascending=False)


# ---------------------------------------------------------------------
# QUANTITATIVE BIAS
# ---------------------------------------------------------------------
def calculate_bias(df_gold, df_dxy, df_us02y):
    signals = {}

    if not df_gold.empty and len(df_gold) > 20:
        close = df_gold["Close"].ffill()

        r = rsi(close).iloc[-1]
        if pd.notna(r):
            signals["RSI momentum"] = float(np.clip(r, 0, 100))

        returns = close.pct_change()
        std = returns.rolling(20).std().iloc[-1]
        mean = returns.rolling(20).mean().iloc[-1]
        z = (returns.iloc[-1] - mean) / (std + 1e-6)
        signals["Price impulse"] = float(np.clip(50 + z * 20, 0, 100))

        ema20 = ema(close, 20).iloc[-1]
        ema50 = ema(close, 50).iloc[-1]
        signals["Trend EMA 20/50"] = (
            75 if close.iloc[-1] > ema20 > ema50
            else 25 if close.iloc[-1] < ema20 < ema50
            else 50
        )

        atr_val = atr(df_gold).iloc[-1]
        if pd.notna(atr_val):
            atr_pct = (atr_val / close.iloc[-1]) * 100
            signals["Volatility stability"] = float(
                np.clip(100 - atr_pct * 20, 0, 100)
            )

    if not df_dxy.empty and len(df_dxy) > 5:
        dxy = df_dxy["Close"].ffill()
        dxy_mom = pct_change(dxy, 5)
        signals["DXY inverse"] = float(np.clip(50 - dxy_mom * 10, 0, 100))

    if not df_us02y.empty and len(df_us02y) > 5:
        y = df_us02y.iloc[:, 0].ffill()
        y_mom = y.iloc[-1] - y.iloc[-6]
        signals["US 2Y inverse"] = float(np.clip(50 - y_mom * 25, 0, 100))

    if not signals:
        return 50.0, "No data", signals

    score = float(np.mean(list(signals.values())))
    label = (
        "Bullish bias"
        if score >= 62
        else "Bearish bias"
        if score <= 38
        else "Neutral bias"
    )
    return score, label, signals


def gauge_chart(score):
    color = T["bull"] if score >= 62 else T["bear"] if score <= 38 else T["neutral"]

    fig = go.Figure(
        go.Indicator(
            mode="gauge",
            value=score,
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickcolor": T["muted"],
                    "tickfont": {"color": T["muted"], "size": 9},
                },
                "bar": {"color": color, "thickness": 0.28},
                "bgcolor": T["panel_2"],
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 38], "color": "rgba(239,98,98,.10)"},
                    {"range": [38, 62], "color": "rgba(216,168,78,.10)"},
                    {"range": [62, 100], "color": "rgba(42,197,139,.10)"},
                ],
            },
        )
    )
    fig.update_layout(
        height=220,
        margin=dict(l=18, r=18, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=T["text"],
    )
    return fig


def chart_layout(**kwargs):
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=T["text"], family="Inter"),
        xaxis=dict(
            gridcolor=T["grid"],
            zerolinecolor=T["grid"],
            showline=False,
        ),
        yaxis=dict(
            gridcolor=T["grid"],
            zerolinecolor=T["grid"],
            showline=False,
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=10, color=T["muted"]),
        ),
    )
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------
# NEWS
# ---------------------------------------------------------------------
def classify_gold_impact(text):
    t = text.lower()

    bullish = [
        "gold up", "gold gains", "gold rises", "gold surges", "gold rallies",
        "gold climbs", "gold jumps", "fed rate cut", "rate cut", "dovish",
        "dollar drops", "dollar falls", "dxy falls", "yields drop",
        "yields fall", "safe haven", "geopolitical tension", "sanctions",
        "trade war", "war",
    ]
    bearish = [
        "gold down", "gold drops", "gold falls", "gold slips", "gold slumps",
        "gold plummets", "gold sinks", "fed rate hike", "rate hike", "hawkish",
        "dollar gains", "dollar rises", "dxy rises", "yields spike",
        "yields rise", "strong dollar", "strong economy",
    ]

    bull_score = sum(k in t for k in bullish)
    bear_score = sum(k in t for k in bearish)

    if bull_score > bear_score:
        return "Bullish"
    if bear_score > bull_score:
        return "Bearish"
    return "Neutral"


@st.cache_data(ttl=180, show_spinner=False)
def get_news(limit=10):
    if not HAS_FEEDPARSER:
        return []

    feeds = [
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=GC=F",
        "https://www.fxstreet.com/rss/news",
        "https://www.investing.com/rss/commodities_Gold.rss",
        "https://www.forexlive.com/feed/news",
    ]

    keywords = [
        "gold", "xau", "dxy", "dollar", "dólar", "fed", "yield", "bond",
        "treasury", "oro", "rate", "inflation", "cpi", "powell", "market",
    ]

    items = []
    seen = set()

    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                title = getattr(entry, "title", "").strip()
                if not title or title in seen:
                    continue

                summary = getattr(entry, "summary", "")
                full_text = f"{title} {summary}"

                dedicated = "GC=F" in feed_url or "Gold.rss" in feed_url
                if not dedicated and not any(k in full_text.lower() for k in keywords):
                    continue

                dt = None
                if getattr(entry, "published_parsed", None):
                    dt = datetime.fromtimestamp(
                        time.mktime(entry.published_parsed), tz=timezone.utc
                    )
                else:
                    dt = datetime.now(timezone.utc)

                items.append(
                    {
                        "title": title,
                        "date": dt,
                        "date_str": getattr(entry, "published", dt.strftime("%Y-%m-%d %H:%M")),
                        "link": getattr(entry, "link", "#"),
                        "impact": classify_gold_impact(full_text),
                    }
                )
                seen.add(title)
        except Exception:
            continue

    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:limit]


# ---------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------
header_logo = (
    f'<img src="{LOGO_SRC}" class="header-logo" alt="CGB">'
    if LOGO_SRC
    else '<div class="header-logo-fallback">CGB</div>'
)

st.markdown(
    f"""
    <div class="terminal-header">
        <div class="header-left">
            {header_logo}
            <div>
                <div class="eyebrow">CGB Research Terminal</div>
                <div class="terminal-title">XAU/USD Market Intelligence</div>
                <div class="terminal-subtitle">
                    Quantitative bias, macro context, institutional positioning and risk.
                </div>
            </div>
        </div>
        <div class="header-status">
            <span class="live-dot"></span>
            <span class="status-text">Market data enabled</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------
# LOAD CORE DATA
# ---------------------------------------------------------------------
with st.spinner("Loading market data..."):
    df_gold = get_price_data("GC=F", period=period_choice)
    df_dxy = get_price_data("DX-Y.NYB", period=period_choice)
    if df_dxy.empty:
        df_dxy = get_price_data("DX=F", period=period_choice)
    df_us02y = get_us02y()

if auto_refresh:
    # Cache TTLs still control actual network frequency.
    pass

gold_ok = not df_gold.empty
dxy_ok = not df_dxy.empty
yield_ok = not df_us02y.empty

# Visible diagnostics: never silently show a blank terminal.
if not gold_ok or not dxy_ok or not yield_ok:
    missing = []
    if not gold_ok:
        missing.append("GC=F (Gold)")
    if not dxy_ok:
        missing.append("DXY")
    if not yield_ok:
        missing.append("US 2Y")
    detail = " · ".join(missing)
    st.warning(
        f"Market data is partially unavailable: {detail}. "
        "The terminal will continue with the sources that are reachable. "
        "Use 'Actualizar datos' after a few seconds if the provider is temporarily rate-limited."
    )


# ---------------------------------------------------------------------
# TOP DATA STRIP
# ---------------------------------------------------------------------
top1, top2, top3, top4 = st.columns(4)

with top1:
    if gold_ok:
        gold_price = float(df_gold["Close"].iloc[-1])
        gold_move = pct_change(df_gold["Close"], 1)
        cls = "metric-positive" if gold_move >= 0 else "metric-negative"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Gold Futures · GC=F</div>
                <div class="metric-value">{fmt_money(gold_price)}</div>
                <div class="metric-sub {cls}">{gold_move:+.2f}% last observation</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="metric-card"><div class="metric-label">Gold Futures</div><div class="metric-value">—</div><div class="metric-sub">Unavailable</div></div>',
            unsafe_allow_html=True,
        )

with top2:
    if dxy_ok:
        dxy_price = float(df_dxy["Close"].iloc[-1])
        dxy_move = pct_change(df_dxy["Close"], 1)
        cls = "metric-positive" if dxy_move <= 0 else "metric-negative"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">US Dollar · DXY</div>
                <div class="metric-value">{dxy_price:,.2f}</div>
                <div class="metric-sub {cls}">{dxy_move:+.2f}% last observation</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="metric-card"><div class="metric-label">US Dollar · DXY</div><div class="metric-value">—</div><div class="metric-sub">Unavailable</div></div>',
            unsafe_allow_html=True,
        )

with top3:
    if yield_ok:
        y = float(df_us02y.iloc[-1, 0])
        y_prev = float(df_us02y.iloc[-2, 0]) if len(df_us02y) > 1 else y
        cls = "metric-positive" if y - y_prev <= 0 else "metric-negative"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">US 2Y Yield</div>
                <div class="metric-value">{y:.2f}%</div>
                <div class="metric-sub {cls}">{y-y_prev:+.02f} pts vs previous</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="metric-card"><div class="metric-label">US 2Y Yield</div><div class="metric-value">—</div><div class="metric-sub">Unavailable</div></div>',
            unsafe_allow_html=True,
        )

with top4:
    score, bias_label, signals = calculate_bias(df_gold, df_dxy, df_us02y)
    score_kind = "bull" if score >= 62 else "bear" if score <= 38 else "neutral"
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">CGB Quant Score</div>
            <div class="metric-value">{score:.0f}/100</div>
            <div class="metric-sub">{status_badge(bias_label, score_kind)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------
# MODULE: OVERVIEW
# ---------------------------------------------------------------------
if st.session_state.module == "Overview":
    st.markdown(
        """
        <div class="section-head">
            <div>
                <div class="section-title">Executive overview</div>
                <div class="section-desc">Lectura rápida del régimen actual de XAU/USD.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([0.85, 1.35], gap="large")

    with left:
        st.markdown('<div class="score-panel">', unsafe_allow_html=True)
        st.markdown('<div class="score-caption">Quantitative bias engine</div>', unsafe_allow_html=True)
        st.plotly_chart(gauge_chart(score), use_container_width=True, config={"displayModeBar": False})
        state_cls = "metric-positive" if score >= 62 else "metric-negative" if score <= 38 else "metric-neutral"
        st.markdown(
            f'<div class="score-state {state_cls}">{bias_label}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Signal decomposition</div>', unsafe_allow_html=True)
        if signals:
            fig = go.Figure(
                go.Bar(
                    x=list(signals.values()),
                    y=list(signals.keys()),
                    orientation="h",
                    marker_color=[
                        T["bull"] if v >= 55 else T["bear"] if v <= 45 else T["neutral"]
                        for v in signals.values()
                    ],
                    text=[f"{v:.0f}" for v in signals.values()],
                    textposition="outside",
                    cliponaxis=False,
                )
            )
            fig.update_layout(
                xaxis_range=[0, 108],
                height=270,
                margin=dict(l=5, r=25, t=10, b=10),
                **chart_layout(),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Insufficient data to calculate the score.")
        st.markdown("</div>", unsafe_allow_html=True)

    if gold_ok:
        dfp, ref_price = pivot_table(df_gold)
        selected = selected_levels(dfp, ref_price, support_count, resistance_count)

        st.markdown(
            f"""
            <div class="section-head">
                <div>
                    <div class="section-title">Key technical levels</div>
                    <div class="section-desc">Reference price {fmt_money(ref_price)} · {resistance_count} resistances + {support_count} supports.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        rows = ""
        for _, row in selected.iterrows():
            if row["Type"] == "Resistance":
                badge = status_badge("Resistance", "bear")
            elif row["Type"] == "Support":
                badge = status_badge("Support", "bull")
            else:
                badge = status_badge("Pivot", "neutral")
            rows += f"""
            <tr>
                <td>{row['Level']}</td>
                <td class="price-cell">{fmt_money(row['Price'])}</td>
                <td>{badge}</td>
                <td class="price-cell">{row['Distance']:+.2f}</td>
            </tr>
            """

        st.markdown(
            f"""
            <div class="panel">
                <table class="level-table">
                    <thead>
                        <tr><th>Level</th><th>Price</th><th>Type</th><th>Distance</th></tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="section-head">
            <div>
                <div class="section-title">Data integrity</div>
                <div class="section-desc">Estado de las principales fuentes consultadas.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.markdown(
            f'<div class="panel panel-tight"><b>GC=F</b><br>{status_badge("Connected" if gold_ok else "Unavailable", "bull" if gold_ok else "bear")}</div>',
            unsafe_allow_html=True,
        )
    with d2:
        st.markdown(
            f'<div class="panel panel-tight"><b>DXY</b><br>{status_badge("Connected" if dxy_ok else "Unavailable", "bull" if dxy_ok else "bear")}</div>',
            unsafe_allow_html=True,
        )
    with d3:
        st.markdown(
            f'<div class="panel panel-tight"><b>US 2Y</b><br>{status_badge("Connected" if yield_ok else "Unavailable", "bull" if yield_ok else "bear")}</div>',
            unsafe_allow_html=True,
        )
    with d4:
        st.markdown(
            f'<div class="panel panel-tight"><b>Interface</b><br>{status_badge(st.session_state.theme, "info")}</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------
# MODULE: GOLD
# ---------------------------------------------------------------------
elif st.session_state.module == "Gold Analysis":
    st.markdown(
        """
        <div class="section-head">
            <div>
                <div class="section-title">Gold analysis</div>
                <div class="section-desc">Price structure, trend, momentum and volatility.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not gold_ok:
        st.error("Gold data is unavailable.")
    else:
        df = df_gold.copy()
        df["EMA20"] = ema(df["Close"], 20)
        df["EMA50"] = ema(df["Close"], 50)
        df["EMA200"] = ema(df["Close"], 200)
        df["B_Upper"], df["B_Mid"], df["B_Lower"] = bollinger_bands(df["Close"])
        df["RSI14"] = rsi(df["Close"])
        df["ATR14"] = atr(df)

        chart = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=.045,
            row_heights=[.75, .25],
        )

        chart.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="XAU/USD",
                increasing_line_color=T["bull"],
                decreasing_line_color=T["bear"],
            ),
            row=1, col=1,
        )

        for col, color, name in [
            ("EMA20", T["primary_2"], "EMA 20"),
            ("EMA50", T["blue"], "EMA 50"),
            ("EMA200", T["muted"], "EMA 200"),
        ]:
            chart.add_trace(
                go.Scatter(
                    x=df.index, y=df[col], line=dict(color=color, width=1.4), name=name
                ),
                row=1, col=1,
            )

        chart.add_trace(
            go.Scatter(
                x=df.index, y=df["B_Upper"],
                line=dict(color=T["muted"], width=1, dash="dot"),
                name="Bollinger upper",
            ),
            row=1, col=1,
        )
        chart.add_trace(
            go.Scatter(
                x=df.index, y=df["B_Lower"],
                line=dict(color=T["muted"], width=1, dash="dot"),
                name="Bollinger lower",
            ),
            row=1, col=1,
        )

        chart.add_trace(
            go.Scatter(
                x=df.index, y=df["RSI14"],
                line=dict(color=T["primary_2"], width=1.4),
                name="RSI 14",
            ),
            row=2, col=1,
        )
        chart.add_hline(y=70, line_dash="dot", line_color=T["bear"], row=2, col=1)
        chart.add_hline(y=30, line_dash="dot", line_color=T["bull"], row=2, col=1)

        chart.update_layout(
            height=650,
            xaxis_rangeslider_visible=False,
            margin=dict(l=10, r=10, t=25, b=10),
            hovermode="x unified",
            **chart_layout(),
        )
        st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})

        c1, c2, c3, c4 = st.columns(4)
        close = df["Close"]
        rsi_val = df["RSI14"].iloc[-1]
        atr_val = df["ATR14"].iloc[-1]
        ema_state = "Above EMA 50" if close.iloc[-1] > df["EMA50"].iloc[-1] else "Below EMA 50"

        c1.metric("RSI 14", f"{rsi_val:.1f}" if pd.notna(rsi_val) else "—")
        c2.metric("ATR 14", fmt_money(atr_val) if pd.notna(atr_val) else "—")
        c3.metric("EMA 20", fmt_money(df["EMA20"].iloc[-1]))
        c4.metric("Structure", ema_state)

        if show_volume and "Volume" in df.columns:
            v1, v2 = st.columns(2)
            with v1:
                fig = go.Figure(go.Bar(
                    x=df.index, y=df["Volume"], marker_color=T["blue"], name="Volume"
                ))
                fig.update_layout(
                    height=250,
                    title="Volume",
                    margin=dict(l=10, r=10, t=35, b=10),
                    **chart_layout(),
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            with v2:
                fig = go.Figure(go.Scatter(
                    x=df.index, y=df["ATR14"],
                    line=dict(color=T["bear"], width=1.8), name="ATR 14"
                ))
                fig.update_layout(
                    height=250,
                    title="ATR 14 · Daily volatility",
                    margin=dict(l=10, r=10, t=35, b=10),
                    **chart_layout(),
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ---------------------------------------------------------------------
# MODULE: MACRO
# ---------------------------------------------------------------------
elif st.session_state.module == "Macro & Correlation":
    st.markdown(
        """
        <div class="section-head">
            <div>
                <div class="section-title">Macro & correlation</div>
                <div class="section-desc">Dollar, front-end rates and their relationship with gold.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if gold_ok and dxy_ok:
        gold_returns = df_gold["Close"].pct_change()
        dxy_returns = df_dxy["Close"].pct_change()
        corr = pd.DataFrame({"Gold": gold_returns, "DXY": dxy_returns}).dropna()
        rolling_corr = corr["Gold"].rolling(30).corr(corr["DXY"]).dropna()
        corr_val = rolling_corr.iloc[-1] if not rolling_corr.empty else np.nan
        dxy_5d = pct_change(df_dxy["Close"], 5)

        if dxy_5d < 0 and pd.notna(corr_val) and corr_val < -0.3:
            scenario = "USD weakness is currently supportive for gold."
            reason = f"DXY is {dxy_5d:+.2f}% over 5 sessions and the 30-session correlation is {corr_val:.2f}."
            kind = "bull"
        elif dxy_5d > 0 and pd.notna(corr_val) and corr_val < -0.3:
            scenario = "USD strength is currently a headwind for gold."
            reason = f"DXY is {dxy_5d:+.2f}% over 5 sessions and the 30-session correlation is {corr_val:.2f}."
            kind = "bear"
        else:
            scenario = "Macro relationship is mixed or temporarily decoupled."
            reason = f"DXY 5-session change: {dxy_5d:+.2f}%. 30-session correlation: {corr_val:.2f}."
            kind = "neutral"

        st.markdown(
            f"""
            <div class="signal-box">
                <div class="signal-kicker">Macro regime</div>
                <div class="signal-title">{status_badge(kind.upper(), kind)} {scenario}</div>
                <p class="signal-text">{reason}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    a, b = st.columns(2)
    with a:
        if dxy_ok:
            fig = go.Figure(go.Candlestick(
                x=df_dxy.index,
                open=df_dxy["Open"],
                high=df_dxy["High"],
                low=df_dxy["Low"],
                close=df_dxy["Close"],
                name="DXY",
                increasing_line_color=T["bear"],
                decreasing_line_color=T["bull"],
            ))
            fig.update_layout(
                height=360,
                xaxis_rangeslider_visible=False,
                title="US Dollar Index",
                margin=dict(l=10, r=10, t=35, b=10),
                **chart_layout(),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with b:
        if yield_ok:
            fig = go.Figure(go.Scatter(
                x=df_us02y.index,
                y=df_us02y.iloc[:, 0],
                line=dict(color=T["primary_2"], width=1.8),
                fill="tozeroy",
                fillcolor="rgba(216,168,78,.08)",
                name="US 2Y",
            ))
            fig.update_layout(
                height=360,
                title="US 2Y Yield",
                margin=dict(l=10, r=10, t=35, b=10),
                **chart_layout(),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    if gold_ok and dxy_ok:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=rolling_corr.index,
                y=rolling_corr,
                line=dict(color=T["blue"], width=2),
                name="30-session correlation",
            )
        )
        fig.add_hline(y=0, line_dash="dot", line_color=T["muted"])
        fig.update_layout(
            height=290,
            title="Gold / DXY rolling correlation · 30 sessions",
            yaxis_range=[-1, 1],
            margin=dict(l=10, r=10, t=35, b=10),
            **chart_layout(),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ---------------------------------------------------------------------
# MODULE: COT
# ---------------------------------------------------------------------
elif st.session_state.module == "COT Positioning":
    st.markdown(
        """
        <div class="section-head">
            <div>
                <div class="section-title">COT positioning</div>
                <div class="section-desc">CFTC positioning by major participant groups.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cot = get_cot_gold()
    if cot.empty:
        st.warning("CFTC data is currently unavailable.")
    else:
        last = cot.iloc[-1]
        report_date = last["report_date_as_yyyy_mm_dd"].strftime("%d/%m/%Y")

        c_long = safe_float(last.get(
            "comm_positions_long_all",
            safe_float(last.get("prod_merc_positions_long_all", 0))
            + safe_float(last.get("swap_positions_long_all", 0))
        ), 0)
        c_short = safe_float(last.get(
            "comm_positions_short_all",
            safe_float(last.get("prod_merc_positions_short_all", 0))
            + safe_float(last.get("swap_positions_short_all", 0))
        ), 0)

        nc_long = safe_float(last.get(
            "noncomm_positions_long_all",
            safe_float(last.get("m_money_positions_long_all", 0))
            + safe_float(last.get("other_rept_positions_long_all", 0))
        ), 0)
        nc_short = safe_float(last.get(
            "noncomm_positions_short_all",
            safe_float(last.get("m_money_positions_short_all", 0))
            + safe_float(last.get("other_rept_positions_short_all", 0))
        ), 0)

        sw_long = safe_float(last.get("swap_positions_long_all", 0), 0)
        sw_short = safe_float(last.get("swap_positions_short_all", 0), 0)
        mm_long = safe_float(last.get("m_money_positions_long_all", 0), 0)
        mm_short = safe_float(last.get("m_money_positions_short_all", 0), 0)

        groups = [
            ("Commercials", c_long, c_short),
            ("Non-commercials", nc_long, nc_short),
            ("Swap dealers", sw_long, sw_short),
            ("Managed money", mm_long, mm_short),
        ]

        st.caption(f"Latest report: {report_date}")

        cols = st.columns(4)
        for col, (title, long_v, short_v) in zip(cols, groups):
            net = long_v - short_v
            kind = "bull" if net >= 0 else "bear"
            with col:
                st.markdown(
                    f"""
                    <div class="cot-card">
                        <div class="cot-title">{title}</div>
                        {status_badge("NET LONG" if net >= 0 else "NET SHORT", kind)}
                        <div class="cot-net {'metric-positive' if net >= 0 else 'metric-negative'}">{net:+,.0f}</div>
                        <div class="data-row"><span class="data-key">Longs</span><span class="data-value">{long_v:,.0f}</span></div>
                        <div class="data-row"><span class="data-key">Shorts</span><span class="data-value">{short_v:,.0f}</span></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        fig = go.Figure()
        if "noncomm_positions_long_all" in cot:
            fig.add_trace(go.Scatter(
                x=cot["report_date_as_yyyy_mm_dd"],
                y=pd.to_numeric(cot["noncomm_positions_long_all"], errors="coerce"),
                name="Non-commercial longs",
                line=dict(color=T["bull"], width=1.8),
            ))
        if "noncomm_positions_short_all" in cot:
            fig.add_trace(go.Scatter(
                x=cot["report_date_as_yyyy_mm_dd"],
                y=pd.to_numeric(cot["noncomm_positions_short_all"], errors="coerce"),
                name="Non-commercial shorts",
                line=dict(color=T["bear"], width=1.8),
            ))
        if "comm_positions_long_all" in cot:
            fig.add_trace(go.Scatter(
                x=cot["report_date_as_yyyy_mm_dd"],
                y=pd.to_numeric(cot["comm_positions_long_all"], errors="coerce"),
                name="Commercial longs",
                line=dict(color=T["blue"], width=1.5, dash="dot"),
            ))

        fig.update_layout(
            height=420,
            title="Historical contract positioning",
            margin=dict(l=10, r=10, t=35, b=10),
            hovermode="x unified",
            **chart_layout(),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ---------------------------------------------------------------------
# MODULE: OPTIONS
# ---------------------------------------------------------------------
elif st.session_state.module == "Options Structure":
    st.markdown(
        """
        <div class="section-head">
            <div>
                <div class="section-title">Options structure</div>
                <div class="section-desc">Open-interest concentration around GLD / IAU reference prices.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    calls, puts, exp, ticker_used, spot_etf = get_options_walls()

    if calls.empty and puts.empty:
        st.info("No options open-interest data is available at the moment.")
    else:
        top_call = calls.loc[calls["openInterest"].idxmax()] if not calls.empty else None
        top_put = puts.loc[puts["openInterest"].idxmax()] if not puts.empty else None

        if top_call is not None and top_put is not None:
            c_strike = float(top_call["strike"])
            p_strike = float(top_put["strike"])
            st.markdown(
                f"""
                <div class="signal-box">
                    <div class="signal-kicker">Largest open-interest concentrations</div>
                    <div class="signal-title">Reference range: {p_strike:.2f} — {c_strike:.2f}</div>
                    <p class="signal-text">
                        Highest call concentration: {c_strike:.2f} · {top_call['openInterest']:,.0f} contracts.
                        Highest put concentration: {p_strike:.2f} · {top_put['openInterest']:,.0f} contracts.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=calls["strike"], y=calls["openInterest"],
            name="Calls",
            marker_color=T["bull"],
        ))
        fig.add_trace(go.Bar(
            x=puts["strike"], y=puts["openInterest"],
            name="Puts",
            marker_color=T["bear"],
        ))
        fig.update_layout(
            height=450,
            barmode="group",
            title=f"{ticker_used} · expiry {exp}",
            xaxis_title="Strike",
            yaxis_title="Open interest",
            margin=dict(l=10, r=10, t=35, b=10),
            **chart_layout(),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        if spot_etf is not None:
            st.caption(f"ETF reference price: {spot_etf:.2f}")


# ---------------------------------------------------------------------
# MODULE: RISK
# ---------------------------------------------------------------------
elif st.session_state.module == "Risk Management":
    st.markdown(
        """
        <div class="section-head">
            <div>
                <div class="section-title">Risk management</div>
                <div class="section-desc">Position sizing for XAU/USD using account risk and stop distance.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    default_entry = float(df_gold["Close"].iloc[-1]) if gold_ok else 2500.0

    c1, c2, c3 = st.columns(3)
    with c1:
        balance = st.number_input("Account balance", min_value=100.0, value=10000.0, step=500.0)
    with c2:
        risk_pct = st.number_input("Risk per trade (%)", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
    with c3:
        contract_value = st.number_input(
            "USD P/L per $1 move / lot",
            min_value=1.0,
            value=100.0,
            step=1.0,
            help="Adjust this to match the exact contract specification of your broker.",
        )

    c4, c5, c6 = st.columns(3)
    with c4:
        entry_price = st.number_input("Entry price", min_value=100.0, value=default_entry)
    with c5:
        sl_price = st.number_input("Stop loss", min_value=100.0, value=max(100.0, default_entry - 15.0))
    with c6:
        tp_price = st.number_input("Take profit", min_value=100.0, value=default_entry + 30.0)

    risk_amount = balance * risk_pct / 100
    sl_distance = abs(entry_price - sl_price)
    tp_distance = abs(tp_price - entry_price)

    if sl_distance <= 0:
        st.error("Stop loss must be different from entry.")
    else:
        lot_size = risk_amount / (sl_distance * contract_value)
        rr = tp_distance / sl_distance if sl_distance else np.nan
        profit = lot_size * tp_distance * contract_value

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Suggested size", f"{lot_size:.2f} lots")
        r2.metric("Maximum risk", fmt_money(risk_amount))
        r3.metric("Potential P/L", fmt_money(profit))
        r4.metric("Risk / reward", f"1 : {rr:.2f}")

        st.markdown(
            f"""
            <div class="signal-box">
                <div class="signal-kicker">Position sizing audit</div>
                <div class="signal-title">Risk distance: {sl_distance:.2f} · Target distance: {tp_distance:.2f}</div>
                <p class="signal-text">
                    This calculation is mathematical only. Verify the contract size, tick value,
                    margin and execution rules with your broker before trading.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------
# MODULE: NEWS
# ---------------------------------------------------------------------
elif st.session_state.module == "News Flow":
    st.markdown(
        """
        <div class="section-head">
            <div>
                <div class="section-title">News flow</div>
                <div class="section-desc">Recent headlines filtered for gold, USD, rates and macro catalysts.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    max_news = st.slider("Headlines to display", 3, 20, 10)
    news = get_news(max_news)

    if not news:
        st.info("No relevant headlines are available right now.")
    else:
        bullish = sum(n["impact"] == "Bullish" for n in news)
        bearish = sum(n["impact"] == "Bearish" for n in news)
        neutral = len(news) - bullish - bearish

        n1, n2, n3 = st.columns(3)
        n1.metric("Bullish", bullish)
        n2.metric("Bearish", bearish)
        n3.metric("Neutral", neutral)

        if bullish > bearish:
            flow_text = "Headline flow is currently skewed bullish."
            flow_kind = "bull"
        elif bearish > bullish:
            flow_text = "Headline flow is currently skewed bearish."
            flow_kind = "bear"
        else:
            flow_text = "Headline flow is currently balanced."
            flow_kind = "neutral"

        st.markdown(
            f"""
            <div class="signal-box">
                <div class="signal-kicker">News regime</div>
                <div class="signal-title">{status_badge(flow_kind.upper(), flow_kind)} {flow_text}</div>
                <p class="signal-text">
                    Classification is keyword-based and should be treated as a screening layer,
                    not as a substitute for reading the source article.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for item in news:
            impact = item["impact"]
            kind = "bull" if impact == "Bullish" else "bear" if impact == "Bearish" else "neutral"
            st.markdown(
                f"""
                <div class="news-card">
                    <div class="news-top">
                        {status_badge(impact, kind)}
                        <span class="news-time">{item['date_str']}</span>
                    </div>
                    <a class="news-link" href="{item['link']}" target="_blank">{item['title']}</a>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------
# FOOTER
# ---------------------------------------------------------------------
st.markdown(
    """
    <div class="footer">
        <b>CGB TERMINAL</b> · XAU/USD Market Intelligence<br>
        Market data may be delayed, incomplete or unavailable. The application is for
        informational and educational purposes only and does not constitute financial advice.
    </div>
    """,
    unsafe_allow_html=True,
)
