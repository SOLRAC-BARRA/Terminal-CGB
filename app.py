# -*- coding: utf-8 -*-
"""
CGB TERMINAL — XAU/USD
Institutional-Grade Quantitative Market Intelligence Terminal
"""

import os
import base64
import time
from datetime import datetime, timezone
from io import StringIO

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
# CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="CGB Terminal | XAU/USD",
    page_icon="logo.jpg" if os.path.exists("logo.jpg") else "📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------
# PALETAS DE COLOR INSTITUCIONALES
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

if "theme" not in st.session_state:
    st.session_state.theme = "Institutional Dark"
if "module" not in st.session_state:
    st.session_state.module = "Overview"

T = THEMES[st.session_state.theme]


# ---------------------------------------------------------------------
# UTILIDADES & HELPERS
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
        val = float(value)
        return val if not np.isnan(val) else default
    except Exception:
        return default

def fmt_money(value, decimals=2):
    val = safe_float(value)
    if np.isnan(val):
        return "—"
    return f"${val:,.{decimals}f}"

def fmt_num(value, decimals=2):
    val = safe_float(value)
    if np.isnan(val):
        return "—"
    return f"{val:,.{decimals}f}"

def pct_change(series, periods=1):
    if series is None or len(series) <= periods or series.empty:
        return 0.0
    val_curr = safe_float(series.iloc[-1])
    val_prev = safe_float(series.iloc[-1 - periods])
    if np.isnan(val_curr) or np.isnan(val_prev) or val_prev == 0:
        return 0.0
    return ((val_curr / val_prev) - 1.0) * 100.0

def status_badge(text, kind="neutral"):
    cls_map = {
        "bull": "badge badge-bull",
        "bear": "badge badge-bear",
        "neutral": "badge badge-neutral",
        "info": "badge badge-info",
    }
    cls = cls_map.get(kind, "badge badge-neutral")
    return f'<span class="{cls}">{text}</span>'


# ---------------------------------------------------------------------
# ESTILOS CSS
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
        background-size: 480px;
        opacity: 0.02;
        pointer-events: none;
        z-index: 0;
    }}
    """

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap');

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

    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background: var(--bg); color: var(--text); }}
    {logo_watermark}
    #MainMenu, footer, header {{ visibility: hidden; }}

    .block-container {{
        max-width: 1680px;
        padding-top: 1.2rem;
        padding-bottom: 2.5rem;
        position: relative;
        z-index: 1;
    }}

    section[data-testid="stSidebar"] {{
        background: var(--panel);
        border-right: 1px solid var(--border);
    }}

    .sidebar-brand {{
        display:flex;
        align-items:center;
        gap:12px;
        padding: 4px 4px 18px 4px;
        border-bottom:1px solid var(--border);
        margin-bottom:16px;
    }}

    .brand-mark {{
        width:40px; height:40px;
        border-radius:8px;
        display:flex; align-items:center; justify-content:center;
        overflow:hidden;
        background:linear-gradient(145deg, var(--primary), var(--primary2));
        color:#111; font-weight:800;
    }}

    .brand-mark img {{ width:100%; height:100%; object-fit:cover; }}
    .brand-name {{ font-size:0.95rem; font-weight:800; color:var(--text); line-height:1.1; }}
    .brand-sub {{ color:var(--muted); font-size:0.65rem; margin-top:3px; letter-spacing:.08em; text-transform:uppercase; }}
    .side-section {{ color:var(--muted); font-size:0.65rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; margin:16px 0 6px; }}

    .terminal-header {{
        display:flex; align-items:center; justify-content:space-between;
        gap:20px; padding:16px 20px;
        background:linear-gradient(135deg, var(--panel) 0%, var(--panel2) 100%);
        border:1px solid var(--border); border-radius:12px;
        margin-bottom:16px;
    }}

    .header-left {{ display:flex; align-items:center; gap:14px; min-width:0; }}
    .header-logo {{ width:44px; height:44px; border-radius:8px; object-fit:cover; border:1px solid var(--border); }}
    .header-logo-fallback {{ width:44px; height:44px; border-radius:8px; background:linear-gradient(145deg,var(--primary),var(--primary2)); color:#111; display:flex; align-items:center; justify-content:center; font-weight:900; }}
    .eyebrow {{ color:var(--primary2); font-size:.65rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; margin-bottom:2px; }}
    .terminal-title {{ font-size:1.35rem; line-height:1.1; font-weight:800; color:var(--text); }}
    .terminal-subtitle {{ margin-top:4px; color:var(--muted); font-size:.75rem; }}

    .metric-card {{
        background:var(--panel); border:1px solid var(--border);
        border-radius:10px; padding:12px 14px; min-height:88px;
    }}
    .metric-label {{ color:var(--muted); font-size:.65rem; font-weight:800; text-transform:uppercase; letter-spacing:.08em; }}
    .metric-value {{ font-family:'JetBrains Mono', monospace; font-size:1.25rem; font-weight:700; color:var(--text); margin-top:5px; }}
    .metric-sub {{ font-size:.70rem; color:var(--muted); margin-top:4px; }}
    .metric-positive {{ color:var(--bull) !important; }}
    .metric-negative {{ color:var(--bear) !important; }}
    .metric-neutral {{ color:var(--neutral) !important; }}

    .panel {{ background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:16px; margin-bottom:14px; }}
    .panel-tight {{ padding:12px 14px; margin-bottom:0; }}
    
    .score-panel {{ background:linear-gradient(145deg,var(--panel),var(--panel2)); border:1px solid var(--border); border-radius:12px; padding:16px; height:100%; display:flex; flex-direction:column; justify-content:center; align-items:center; }}
    .score-caption {{ color:var(--muted); font-size:.68rem; font-weight:800; text-transform:uppercase; letter-spacing:.10em; text-align:center; margin-bottom:8px; }}
    .score-state {{ font-size:.9rem; font-weight:800; letter-spacing:.05em; text-transform:uppercase; margin-top:6px; text-align:center; }}

    .badge {{ display:inline-flex; align-items:center; border-radius:4px; padding:3px 7px; font-size:.62rem; font-weight:800; letter-spacing:.06em; text-transform:uppercase; border:1px solid transparent; }}
    .badge-bull {{ color:var(--bull); background:rgba(42,197,139,.12); border-color:rgba(42,197,139,.25); }}
    .badge-bear {{ color:var(--bear); background:rgba(239,98,98,.12); border-color:rgba(239,98,98,.25); }}
    .badge-neutral {{ color:var(--neutral); background:rgba(216,168,78,.12); border-color:rgba(216,168,78,.25); }}
    .badge-info {{ color:var(--blue); background:rgba(93,169,233,.12); border-color:rgba(93,169,233,.25); }}

    .level-table {{ width:100%; border-collapse:collapse; font-size:.78rem; }}
    .level-table th {{ color:var(--muted); font-size:.64rem; text-transform:uppercase; letter-spacing:.08em; text-align:left; padding:8px 12px; border-bottom:1px solid var(--border); }}
    .level-table td {{ padding:10px 12px; border-bottom:1px solid var(--border); color:var(--text); }}
    .price-cell {{ font-family:'JetBrains Mono',monospace; font-weight:700; }}

    .signal-box {{ border:1px solid var(--border); background:linear-gradient(135deg,var(--panel),var(--panel2)); border-radius:10px; padding:14px 16px; margin-bottom:14px; }}
    .signal-kicker {{ color:var(--primary2); font-size:.64rem; font-weight:800; letter-spacing:.11em; text-transform:uppercase; }}
    .signal-title {{ font-size:1.0rem; font-weight:800; margin:4px 0; color:var(--text); display:flex; align-items:center; gap:10px; }}
    .signal-text {{ font-size:.78rem; color:var(--muted); line-height:1.5; margin:0; }}

    .news-card {{ background:var(--panel); border:1px solid var(--border); border-radius:8px; padding:12px 14px; margin-bottom:8px; }}
    .news-top {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:6px; }}
    .news-time {{ color:var(--muted); font-size:.68rem; }}
    .news-link {{ color:var(--text) !important; text-decoration:none !important; font-size:.82rem; font-weight:600; line-height:1.4; }}

    .footer {{ border-top:1px solid var(--border); margin-top:24px; padding:16px 0 0; color:var(--muted); font-size:.68rem; text-align:center; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------
# SIDEBAR / NAVEGACIÓN
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
                <div class="brand-sub">XAU/USD Intelligence</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="side-section">Módulos</div>', unsafe_allow_html=True)
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

    st.markdown('<div class="side-section">Interfaz</div>', unsafe_allow_html=True)
    selected_theme = st.selectbox(
        "Tema visual",
        list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.theme),
        label_visibility="collapsed",
    )
    if selected_theme != st.session_state.theme:
        st.session_state.theme = selected_theme
        st.rerun()

    st.markdown('<div class="side-section">Configuración</div>', unsafe_allow_html=True)
    period_choice = st.selectbox("Ventana de tiempo", ["3mo", "6mo", "1y", "2y"], index=2)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        support_count = st.number_input("Soportes", 1, 4, 2, 1)
    with col_s2:
        resistance_count = st.number_input("Resistencias", 1, 4, 2, 1)

    show_volume = st.toggle("Mostrar volumen", value=True)

    if st.button("Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ---------------------------------------------------------------------
# DATA ENGINES (TOLERANTES A FALLOS)
# ---------------------------------------------------------------------
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
}

def get_yf_session():
    if HAS_CURL_CFFI:
        try:
            return curl_requests.Session(impersonate="chrome")
        except Exception:
            return None
    return None

YF_SESSION = get_yf_session()

def _yahoo_chart_request(ticker, period="1y", interval="1d"):
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            url = f"https://{host}/v8/finance/chart/{ticker}"
            res = requests.get(
                url,
                params={"range": period, "interval": interval, "includePrePost": "false"},
                headers=HTTP_HEADERS,
                timeout=10,
            )
            res.raise_for_status()
            payload = res.json()
            result = payload.get("chart", {}).get("result", [None])[0]
            if not result:
                continue

            timestamps = result.get("timestamp", [])
            quote = result.get("indicators", {}).get("quote", [{}])[0]
            if not timestamps or not quote:
                continue

            df = pd.DataFrame({
                "Open": quote.get("open", []),
                "High": quote.get("high", []),
                "Low": quote.get("low", []),
                "Close": quote.get("close", []),
                "Volume": quote.get("volume", []),
            }, index=pd.to_datetime(timestamps, unit="s", utc=True))
            df = df.apply(pd.to_numeric, errors="coerce").dropna(subset=["Close"])
            if not df.empty:
                return df
        except Exception:
            continue
    return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def get_price_data(ticker: str, period="1y", interval="1d"):
    df = _yahoo_chart_request(ticker, period=period, interval=interval)
    if not df.empty:
        return df

    try:
        tk = yf.Ticker(ticker, session=YF_SESSION) if YF_SESSION else yf.Ticker(ticker)
        df_yf = tk.history(period=period, interval=interval, auto_adjust=False)
        if df_yf is not None and not df_yf.empty and "Close" in df_yf.columns:
            return df_yf.dropna(subset=["Close"])
    except Exception:
        pass

    return pd.DataFrame()

@st.cache_data(ttl=600, show_spinner=False)
def get_us02y():
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2"
        res = requests.get(url, headers=HTTP_HEADERS, timeout=10)
        res.raise_for_status()
        df = pd.read_csv(StringIO(res.text))
        df.columns = ["Date", "Close"]
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df = df.dropna(subset=["Date", "Close"]).set_index("Date")
        if not df.empty:
            return df.tail(500)
    except Exception:
        pass

    df_yf = get_price_data("2YY=F", period="1y")
    if not df_yf.empty:
        return df_yf[["Close"]]
    return pd.DataFrame()

@st.cache_data(ttl=1800, show_spinner=False)
def get_cot_gold():
    url_disagg = "https://publicreporting.cftc.gov/resource/kh3c-5v3d.json"
    params = {
        "$where": "cftc_contract_market_code='088691'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": 30,
    }
    try:
        r = requests.get(url_disagg, params=params, timeout=10, headers=HTTP_HEADERS)
        r.raise_for_status()
        rows = r.json()
        if rows:
            df = pd.DataFrame(rows)
            for col in df.columns:
                if "positions" in col or "pct_of_oi" in col or col == "open_interest_all":
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            df["report_date_as_yyyy_mm_dd"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"], errors="coerce")
            return df.sort_values("report_date_as_yyyy_mm_dd")
    except Exception:
        pass
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
            spot_price = float(hist["Close"].iloc[-1])
            for exp in exps[:2]:
                chain = tk.option_chain(exp)
                calls = chain.calls.dropna(subset=["strike", "openInterest"])
                puts = chain.puts.dropna(subset=["strike", "openInterest"])
                calls_f = calls[(calls["strike"] >= spot_price * .85) & (calls["strike"] <= spot_price * 1.15)]
                puts_f = puts[(puts["strike"] >= spot_price * .85) & (puts["strike"] <= spot_price * 1.15)]
                c_agg = calls_f.groupby("strike")["openInterest"].sum().reset_index()
                p_agg = puts_f.groupby("strike")["openInterest"].sum().reset_index()
                if c_agg["openInterest"].sum() > 0 or p_agg["openInterest"].sum() > 0:
                    return c_agg, p_agg, exp, ticker, spot_price
        except Exception:
            continue
    return pd.DataFrame(), pd.DataFrame(), None, None, None


# ---------------------------------------------------------------------
# INDICADORES TÉCNICOS & CÁLCULOS
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
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
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
    
    rows = [
        ("R3", r3, "Resistance"),
        ("R2", r2, "Resistance"),
        ("R1", r1, "Resistance"),
        ("PP · Pivot", pp, "Pivot"),
        ("S1", s1, "Support"),
        ("S2", s2, "Support"),
        ("S3", s3, "Support"),
    ]
    dfp = pd.DataFrame(rows, columns=["Level", "Price", "Type"])
    dfp["Distance"] = dfp["Price"] - current
    return dfp.sort_values("Price", ascending=False), current

def selected_levels(dfp, ref_price, support_n, resistance_n):
    if dfp.empty:
        return dfp
    res = dfp[(dfp["Type"] == "Resistance") & (dfp["Price"] > ref_price)].sort_values("Price").head(resistance_n)
    sup = dfp[(dfp["Type"] == "Support") & (dfp["Price"] < ref_price)].sort_values("Price", ascending=False).head(support_n)
    piv = dfp[dfp["Type"] == "Pivot"]
    return pd.concat([res, piv, sup]).sort_values("Price", ascending=False)

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
        z = (returns.iloc[-1] - mean) / (std + 1e-6) if std > 0 else 0
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
            signals["Volatility stability"] = float(np.clip(100 - atr_pct * 20, 0, 100))

    if not df_dxy.empty and len(df_dxy) > 5:
        dxy = df_dxy["Close"].ffill()
        dxy_mom = pct_change(dxy, 5)
        signals["DXY inverse"] = float(np.clip(50 - dxy_mom * 10, 0, 100))

    if not df_us02y.empty and len(df_us02y) > 5:
        y = df_us02y.iloc[:, 0].ffill()
        y_mom = float(y.iloc[-1] - y.iloc[-6])
        signals["US 2Y inverse"] = float(np.clip(50 - y_mom * 25, 0, 100))

    if not signals:
        return 50.0, "NEUTRAL BIAS", {}

    score = float(np.mean(list(signals.values())))
    label = "BULLISH BIAS" if score >= 62 else "BEARISH BIAS" if score <= 38 else "NEUTRAL BIAS"
    return score, label, signals


# ---------------------------------------------------------------------
# GRÁFICOS INSTITUCIONALES (PLOTLY)
# ---------------------------------------------------------------------
def chart_layout(**kwargs):
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=T["text"], family="Inter"),
        xaxis=dict(gridcolor=T["grid"], zerolinecolor=T["grid"], showline=False),
        yaxis=dict(gridcolor=T["grid"], zerolinecolor=T["grid"], showline=False),
        margin=dict(l=10, r=10, t=25, b=10),
    )
    base.update(kwargs)
    return base

def gauge_chart(score):
    color = T["bull"] if score >= 62 else T["bear"] if score <= 38 else T["neutral"]
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"font": {"size": 38, "color": T["text"], "family": "JetBrains Mono"}, "suffix": ""},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": T["muted"], "tickfont": {"size": 9, "color": T["muted"]}},
                "bar": {"color": color, "thickness": 0.25},
                "bgcolor": T["panel_2"],
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 38], "color": "rgba(239,98,98,.12)"},
                    {"range": [38, 62], "color": "rgba(216,168,78,.12)"},
                    {"range": [62, 100], "color": "rgba(42,197,139,.12)"},
                ],
            },
        )
    )
    fig.update_layout(height=190, margin=dict(l=15, r=15, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


# ---------------------------------------------------------------------
# NOTICIAS / NOTICIAS CON CLASIFICACIÓN
# ---------------------------------------------------------------------
def classify_gold_impact(text):
    t = text.lower()
    bullish = ["gold up", "rises", "surges", "rallies", "rate cut", "dovish", "safe haven", "tension", "inflation"]
    bearish = ["gold down", "falls", "slips", "rate hike", "hawkish", "dollar gains", "yields rise"]
    b_score = sum(k in t for k in bullish)
    r_score = sum(k in t for k in bearish)
    return "Bullish" if b_score > r_score else "Bearish" if r_score > b_score else "Neutral"

@st.cache_data(ttl=300, show_spinner=False)
def get_news(limit=10):
    if not HAS_FEEDPARSER:
        return []
    feeds = ["https://feeds.finance.yahoo.com/rss/2.0/headline?s=GC=F", "https://www.investing.com/rss/commodities_Gold.rss"]
    items = []
    seen = set()
    for f in feeds:
        try:
            parsed = feedparser.parse(f)
            for e in parsed.entries:
                title = getattr(e, "title", "").strip()
                if title and title not in seen:
                    items.append({
                        "title": title,
                        "date_str": getattr(e, "published", "Reciente"),
                        "link": getattr(e, "link", "#"),
                        "impact": classify_gold_impact(title),
                    })
                    seen.add(title)
        except Exception:
            continue
    return items[:limit]


# ---------------------------------------------------------------------
# HEADER & DATOS INICIALES
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
                <div class="terminal-subtitle">Análisis cuantitativo de sesgo, modelo macro, estructura COT y gestión de riesgo.</div>
            </div>
        </div>
        <div class="header-status">
            <span class="badge badge-bull">SISTEMA ACTIVO</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.spinner("Cargando datos de mercado..."):
    df_gold = get_price_data("GC=F", period=period_choice)
    df_dxy = get_price_data("DX-Y.NYB", period=period_choice)
    if df_dxy.empty:
        df_dxy = get_price_data("DX=F", period=period_choice)
    df_us02y = get_us02y()

gold_ok = not df_gold.empty
dxy_ok = not df_dxy.empty
yield_ok = not df_us02y.empty


# ---------------------------------------------------------------------
# BARRA TOP DE MÉTRICAS
# ---------------------------------------------------------------------
top1, top2, top3, top4 = st.columns(4)

with top1:
    if gold_ok:
        gp = float(df_gold["Close"].iloc[-1])
        gm = pct_change(df_gold["Close"], 1)
        cls = "metric-positive" if gm >= 0 else "metric-negative"
        st.markdown(f'<div class="metric-card"><div class="metric-label">Oro Futuros · GC=F</div><div class="metric-value">{fmt_money(gp)}</div><div class="metric-sub {cls}">{gm:+.2f}% (Última sesión)</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="metric-card"><div class="metric-label">Oro Futuros</div><div class="metric-value">—</div><div class="metric-sub">Sin conexión</div></div>', unsafe_allow_html=True)

with top2:
    if dxy_ok:
        dp = float(df_dxy["Close"].iloc[-1])
        dm = pct_change(df_dxy["Close"], 1)
        cls = "metric-positive" if dm <= 0 else "metric-negative"
        st.markdown(f'<div class="metric-card"><div class="metric-label">Dólar Índex · DXY</div><div class="metric-value">{dp:,.2f}</div><div class="metric-sub {cls}">{dm:+.2f}% (Última sesión)</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="metric-card"><div class="metric-label">Dólar Índex</div><div class="metric-value">—</div><div class="metric-sub">Sin conexión</div></div>', unsafe_allow_html=True)

with top3:
    if yield_ok:
        yp = float(df_us02y.iloc[-1, 0])
        yp_prev = float(df_us02y.iloc[-2, 0]) if len(df_us02y) > 1 else yp
        cls = "metric-positive" if yp - yp_prev <= 0 else "metric-negative"
        st.markdown(f'<div class="metric-card"><div class="metric-label">US 2Y Yield</div><div class="metric-value">{yp:.2f}%</div><div class="metric-sub {cls}">{yp-yp_prev:+.2f} pts prev</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="metric-card"><div class="metric-label">US 2Y Yield</div><div class="metric-value">—</div><div class="metric-sub">Sin conexión</div></div>', unsafe_allow_html=True)

with top4:
    score, bias_label, signals = calculate_bias(df_gold, df_dxy, df_us02y)
    score_kind = "bull" if score >= 62 else "bear" if score <= 38 else "neutral"
    st.markdown(f'<div class="metric-card"><div class="metric-label">CGB Quant Score</div><div class="metric-value">{score:.0f}/100</div><div class="metric-sub">{status_badge(bias_label, score_kind)}</div></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------
# MÓDULO 1: OVERVIEW
# ---------------------------------------------------------------------
if st.session_state.module == "Overview":
    left, right = st.columns([0.8, 1.2], gap="large")

    with left:
        st.markdown('<div class="score-panel">', unsafe_allow_html=True)
        st.markdown('<div class="score-caption">Quantitative Bias Engine</div>', unsafe_allow_html=True)
        st.plotly_chart(gauge_chart(score), use_container_width=True, config={"displayModeBar": False})
        state_cls = "metric-positive" if score >= 62 else "metric-negative" if score <= 38 else "metric-neutral"
        st.markdown(f'<div class="score-state {state_cls}">{bias_label}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label" style="margin-bottom:10px;">Signal Decomposition</div>', unsafe_allow_html=True)
        if signals:
            fig = go.Figure(
                go.Bar(
                    x=list(signals.values()),
                    y=list(signals.keys()),
                    orientation="h",
                    marker_color=[T["bull"] if v >= 55 else T["bear"] if v <= 45 else T["neutral"] for v in signals.values()],
                    text=[f"{v:.0f}" for v in signals.values()],
                    textposition="outside",
                    cliponaxis=False,
                )
            )
            fig.update_layout(
                xaxis_range=[0, 110],
                height=230,
                **chart_layout(margin=dict(l=10, r=20, t=10, b=10))
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Insuficientes datos para desglose.")
        st.markdown("</div>", unsafe_allow_html=True)

    if gold_ok:
        dfp, ref_price = pivot_table(df_gold)
        selected = selected_levels(dfp, ref_price, support_count, resistance_count)

        rows = ""
        for _, row in selected.iterrows():
            badge = status_badge("Resistencia", "bear") if row["Type"] == "Resistance" else status_badge("Soporte", "bull") if row["Type"] == "Support" else status_badge("Pivote", "neutral")
            rows += f"<tr><td><b>{row['Level']}</b></td><td class=\"price-cell\">{fmt_money(row['Price'])}</td><td>{badge}</td><td class=\"price-cell\">{row['Distance']:+.2f}</td></tr>"

        st.markdown(
            f"""
            <div class="panel">
                <div class="metric-label" style="margin-bottom:12px;">Niveles Técnicos Clave (Ref. {fmt_money(ref_price)})</div>
                <table class="level-table">
                    <thead><tr><th>Nivel</th><th>Precio</th><th>Tipo</th><th>Distancia</th></tr></thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="metric-label" style="margin: 15px 0 8px;">Integridad del Sistema</div>', unsafe_allow_html=True)
    d1, d2, d3, d4 = st.columns(4)
    d1.markdown(f'<div class="panel panel-tight"><b>GC=F (Oro)</b><br>{status_badge("Conectado" if gold_ok else "Error", "bull" if gold_ok else "bear")}</div>', unsafe_allow_html=True)
    d2.markdown(f'<div class="panel panel-tight"><b>DXY (Dólar)</b><br>{status_badge("Conectado" if dxy_ok else "Error", "bull" if dxy_ok else "bear")}</div>', unsafe_allow_html=True)
    d3.markdown(f'<div class="panel panel-tight"><b>US 2Y (Tipos)</b><br>{status_badge("Conectado" if yield_ok else "Error", "bull" if yield_ok else "bear")}</div>', unsafe_allow_html=True)
    d4.markdown(f'<div class="panel panel-tight"><b>Tema Activo</b><br>{status_badge(st.session_state.theme, "info")}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------
# MÓDULO 2: GOLD ANALYSIS
# ---------------------------------------------------------------------
elif st.session_state.module == "Gold Analysis":
    if not gold_ok:
        st.error("Datos del oro no disponibles actualmente.")
    else:
        df = df_gold.copy()
        df["EMA20"] = ema(df["Close"], 20)
        df["EMA50"] = ema(df["Close"], 50)
        df["B_Upper"], df["B_Mid"], df["B_Lower"] = bollinger_bands(df["Close"])
        df["RSI14"] = rsi(df["Close"])
        df["ATR14"] = atr(df)

        chart = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=.05, row_heights=[.75, .25])
        chart.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="XAU/USD", increasing_line_color=T["bull"], decreasing_line_color=T["bear"]), row=1, col=1)
        chart.add_trace(go.Scatter(x=df.index, y=df["EMA20"], line=dict(color=T["primary_2"], width=1.2), name="EMA 20"), row=1, col=1)
        chart.add_trace(go.Scatter(x=df.index, y=df["EMA50"], line=dict(color=T["blue"], width=1.2), name="EMA 50"), row=1, col=1)
        chart.add_trace(go.Scatter(x=df.index, y=df["RSI14"], line=dict(color=T["primary2"], width=1.4), name="RSI 14"), row=2, col=1)
        chart.add_hline(y=70, line_dash="dot", line_color=T["bear"], row=2, col=1)
        chart.add_hline(y=30, line_dash="dot", line_color=T["bull"], row=2, col=1)

        chart.update_layout(height=580, xaxis_rangeslider_visible=False, hovermode="x unified", **chart_layout())
        st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("RSI (14)", f"{df['RSI14'].iloc[-1]:.1f}" if pd.notna(df['RSI14'].iloc[-1]) else "—")
        c2.metric("ATR (14)", fmt_money(df["ATR14"].iloc[-1]))
        c3.metric("EMA 20", fmt_money(df["EMA20"].iloc[-1]))
        c4.metric("Tendencia", "Alcista > EMA50" if df["Close"].iloc[-1] > df["EMA50"].iloc[-1] else "Bajista < EMA50")


# ---------------------------------------------------------------------
# MÓDULO 3: MACRO & CORRELATION
# ---------------------------------------------------------------------
elif st.session_state.module == "Macro & Correlation":
    if gold_ok and dxy_ok:
        g_ret = df_gold["Close"].pct_change()
        d_ret = df_dxy["Close"].pct_change()
        corr_df = pd.DataFrame({"Gold": g_ret, "DXY": d_ret}).dropna()
        rolling = corr_df["Gold"].rolling(30).corr(corr_df["DXY"]).dropna()
        c_val = rolling.iloc[-1] if not rolling.empty else 0.0

        st.markdown(
            f"""
            <div class="signal-box">
                <div class="signal-kicker">Régimen Macro Actual</div>
                <div class="signal-title">Correlación 30D (Oro / DXY): {c_val:.2f}</div>
                <p class="signal-text">Un valor marcadamente negativo indica acoplamiento inverso tradicional (Dólar débil = Oro fuerte).</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    m1, m2 = st.columns(2)
    with m1:
        if dxy_ok:
            fig = go.Figure(go.Candlestick(x=df_dxy.index, open=df_dxy["Open"], high=df_dxy["High"], low=df_dxy["Low"], close=df_dxy["Close"], name="DXY", increasing_line_color=T["bear"], decreasing_line_color=T["bull"]))
            fig.update_layout(height=340, xaxis_rangeslider_visible=False, title="Dólar Index (DXY)", **chart_layout())
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with m2:
        if yield_ok:
            fig = go.Figure(go.Scatter(x=df_us02y.index, y=df_us02y.iloc[:, 0], line=dict(color=T["primary_2"], width=1.8), fill="tozeroy", name="US 2Y"))
            fig.update_layout(height=340, title="Rendimiento Bono EE.UU. 2A", **chart_layout())
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ---------------------------------------------------------------------
# MÓDULO 4: COT POSITIONING
# ---------------------------------------------------------------------
elif st.session_state.module == "COT Positioning":
    cot = get_cot_gold()
    if cot.empty:
        st.warning("Datos del CFTC no disponibles temporalmente.")
    else:
        last = cot.iloc[-1]
        date_str = last["report_date_as_yyyy_mm_dd"].strftime("%d/%m/%Y")
        st.caption(f"Último reporte COT oficial publicado: {date_str}")

        nc_long = safe_float(last.get("noncomm_positions_long_all", 0))
        nc_short = safe_float(last.get("noncomm_positions_short_all", 0))
        c_long = safe_float(last.get("comm_positions_long_all", 0))
        c_short = safe_float(last.get("comm_positions_short_all", 0))

        net_nc = nc_long - nc_short
        net_c = c_long - c_short

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'<div class="panel"><b>Especuladores (Non-Commercial)</b><br><h3 class="{ "metric-positive" if net_nc>=0 else "metric-negative" }">{net_nc:+,.0f} contratos</h3>Longs: {nc_long:,.0f} | Shorts: {nc_short:,.0f}</div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="panel"><b>Comerciales / Coberturas</b><br><h3 class="{ "metric-positive" if net_c>=0 else "metric-negative" }">{net_c:+,.0f} contratos</h3>Longs: {c_long:,.0f} | Shorts: {c_short:,.0f}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------
# MÓDULO 5: OPTIONS STRUCTURE
# ---------------------------------------------------------------------
elif st.session_state.module == "Options Structure":
    calls, puts, exp, ticker, spot = get_options_walls()
    if calls.empty and puts.empty:
        st.info("Estructura de opciones no disponible en este momento.")
    else:
        st.markdown(f'<div class="signal-box"><div class="signal-kicker">ETF Referencia: {ticker}</div><div class="signal-title">Vencimiento: {exp} · Precio Spot: ${spot:.2f}</div></div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=calls["strike"], y=calls["openInterest"], name="Calls", marker_color=T["bull"]))
        fig.add_trace(go.Bar(x=puts["strike"], y=puts["openInterest"], name="Puts", marker_color=T["bear"]))
        fig.update_layout(height=420, barmode="group", title="Open Interest por Strike", **chart_layout())
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ---------------------------------------------------------------------
# MÓDULO 6: RISK MANAGEMENT
# ---------------------------------------------------------------------
elif st.session_state.module == "Risk Management":
    default_entry = float(df_gold["Close"].iloc[-1]) if gold_ok else 2500.0

    c1, c2, c3 = st.columns(3)
    with c1:
        balance = st.number_input("Balance de cuenta ($)", min_value=100.0, value=10000.0, step=500.0)
    with c2:
        risk_pct = st.number_input("Riesgo por operación (%)", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
    with c3:
        contract_val = st.number_input("Valor por $1 movimiento / Lote", min_value=1.0, value=100.0, step=1.0)

    c4, c5, c6 = st.columns(3)
    with c4:
        entry = st.number_input("Precio entrada", min_value=100.0, value=default_entry)
    with c5:
        sl = st.number_input("Stop Loss", min_value=100.0, value=max(100.0, default_entry - 15.0))
    with c6:
        tp = st.number_input("Take Profit", min_value=100.0, value=default_entry + 30.0)

    risk_amount = balance * (risk_pct / 100.0)
    sl_dist = abs(entry - sl)
    tp_dist = abs(tp - entry)

    if sl_dist > 0:
        lots = risk_amount / (sl_dist * contract_val)
        rr = tp_dist / sl_dist
        profit = lots * tp_dist * contract_val

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Lotaje sugerido", f"{lots:.2f} lotes")
        r2.metric("Riesgo máx.", fmt_money(risk_amount))
        r3.metric("Beneficio est.", fmt_money(profit))
        r4.metric("Ratio R:R", f"1 : {rr:.2f}")


# ---------------------------------------------------------------------
# MÓDULO 7: NEWS FLOW
# ---------------------------------------------------------------------
elif st.session_state.module == "News Flow":
    news = get_news(12)
    if not news:
        st.info("Sin titulares disponibles.")
    else:
        for item in news:
            kind = "bull" if item["impact"] == "Bullish" else "bear" if item["impact"] == "Bearish" else "neutral"
            st.markdown(
                f"""
                <div class="news-card">
                    <div class="news-top">
                        {status_badge(item['impact'], kind)}
                        <span class="news-time">{item['date_str']}</span>
                    </div>
                    <a class="news-link" href="{item['link']}" target="_blank">{item['title']}</a>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------
# FOOTER INSTITUCIONAL
# ---------------------------------------------------------------------
st.markdown(
    """
    <div class="footer">
        <b>CGB TERMINAL</b> · XAU/USD Institutional Research<br>
        Información financiera con fines únicamente educativos y de análisis.
    </div>
    """,
    unsafe_allow_html=True,
)
