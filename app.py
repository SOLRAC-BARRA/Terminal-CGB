# -*- coding: utf-8 -*-
"""
=========================================================
CGB COMUNITY — Terminal Cuantitativo XAU/USD (Versión Pro)
=========================================================
Desarrollado para análisis técnico, macroeconómico y cuantitativo del Oro.
"""

import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
import yfinance as yf

# Intentar importar librerías opcionales
try:
    from curl_cffi import requests as curl_requests
    _HAS_CURL_CFFI = True
except Exception:
    _HAS_CURL_CFFI = False

try:
    import feedparser
    _HAS_FEEDPARSER = True
except Exception:
    _HAS_FEEDPARSER = False


# =========================================================
# CONFIGURACIÓN DE PÁGINA STREAMLIT
# =========================================================
st.set_page_config(
    page_title="CGB COMUNITY | Terminal XAU/USD",
    page_icon="🥇",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# GESTIÓN DE TEMAS VISUALES (ESTILOS Y COLORES)
# =========================================================
THEMES = {
    "🌟 CGB Gold Deluxe (Predeterminado)": {
        "bg": "#0a0c10", "card": "#12151c", "border": "#232733",
        "primary": "#c9a227", "primary_light": "#e8c766", "text": "#eef0f3",
        "muted": "#8b93a3", "bull": "#2fd583", "bear": "#ff5a67", "neutral": "#e8c766", "blue": "#4da6ff"
    },
    "🟦 Midnight Navy": {
        "bg": "#0b132b", "card": "#1c2541", "border": "#3a506b",
        "primary": "#48cae4", "primary_light": "#90e0ef", "text": "#edf6f9",
        "muted": "#8d99ae", "bull": "#06d6a0", "bear": "#ef476f", "neutral": "#ffd166", "blue": "#118ab2"
    },
    "🟢 TradingView Dark": {
        "bg": "#131722", "card": "#1e222d", "border": "#2a2e39",
        "primary": "#2962ff", "primary_light": "#5b8cff", "text": "#d1d4dc",
        "muted": "#787b86", "bull": "#089981", "bear": "#f23645", "neutral": "#ff9800", "blue": "#2962ff"
    },
    "🏛️ Institutional Bloomberg": {
        "bg": "#000000", "card": "#111111", "border": "#2a2a2a",
        "primary": "#ff9900", "primary_light": "#ffb84d", "text": "#00ff00",
        "muted": "#aaaaaa", "bull": "#00ff00", "bear": "#ff0000", "neutral": "#ff9900", "blue": "#00ffff"
    }
}

# Sidebar - Selección de Tema
st.sidebar.markdown("### 🎨 Personalización de Interfaz")
theme_choice = st.sidebar.selectbox("Selecciona un tema visual:", list(THEMES.keys()))
T = THEMES[theme_choice]

# Inyección de CSS dinámico según el tema elegido
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background-color: {T['bg']}; color: {T['text']}; }}
    #MainMenu, footer {{visibility: hidden;}}
    section[data-testid="stSidebar"] {{ background-color: {T['card']}; border-right: 1px solid {T['border']}; }}

    .cgb-header {{
        display: flex; align-items: center; gap: 16px;
        padding: 20px 24px; margin-bottom: 20px;
        background: linear-gradient(135deg, {T['card']} 0%, {T['bg']} 100%);
        border: 1px solid {T['border']}; border-radius: 14px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }}
    .cgb-logo {{
        width: 48px; height: 48px; border-radius: 12px;
        background: linear-gradient(135deg, {T['primary']} 0%, {T['primary_light']} 100%);
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 1.2rem; color: #000; flex-shrink: 0;
    }}
    .cgb-title {{ font-size: 1.5rem; font-weight: 800; color: {T['text']}; letter-spacing: -0.02em; margin: 0; }}
    .cgb-subtitle {{ color: {T['muted']}; font-size: 0.85rem; margin-top: 2px; }}

    .cgb-label {{ color: {T['muted']}; font-size: 0.75rem; text-transform: uppercase; letter-spacing: .08em; font-weight: 700; margin-bottom: 10px; }}
    .cgb-bull {{ color: {T['bull']}; font-weight: 700; }}
    .cgb-bear {{ color: {T['bear']}; font-weight: 700; }}
    .cgb-neutral {{ color: {T['neutral']}; font-weight: 700; }}

    .cgb-news-card {{
        background-color: {T['card']}; border: 1px solid {T['border']}; border-radius: 12px;
        padding: 14px 16px; margin-bottom: 10px; transition: all .2s ease;
    }}
    .cgb-news-card:hover {{ border-color: {T['primary']}; transform: translateY(-2px); }}
    .cgb-news-title {{ color: {T['text']}; text-decoration: none; font-weight: 600; font-size: 0.95rem; }}
    .cgb-news-meta {{ color: {T['muted']}; font-size: 0.75rem; margin-top: 6px; }}

    .cgb-table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
    .cgb-table th {{
        text-align: left; color: {T['muted']}; font-size: 0.7rem; text-transform: uppercase;
        letter-spacing: .06em; padding: 10px; border-bottom: 1px solid {T['border']}; font-weight: 700;
    }}
    .cgb-table td {{ padding: 10px; border-bottom: 1px solid {T['border']}; color: {T['text']}; }}
    .cgb-badge {{
        display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 700;
    }}
    .cgb-badge-res {{ background: rgba(255,90,103,0.15); color: {T['bear']}; border: 1px solid rgba(255,90,103,0.35); }}
    .cgb-badge-sop {{ background: rgba(47,213,131,0.15); color: {T['bull']}; border: 1px solid rgba(47,213,131,0.35); }}
    .cgb-badge-piv {{ background: rgba(232,199,102,0.15); color: {T['neutral']}; border: 1px solid rgba(232,199,102,0.35); }}

    .stTabs [data-baseweb="tab-list"] {{ gap: 6px; border-bottom: 1px solid {T['border']}; }}
    .stTabs [data-baseweb="tab"] {{
        background-color: transparent; border-radius: 8px 8px 0 0; padding: 10px 18px;
        color: {T['muted']}; font-weight: 600;
    }}
    .stTabs [aria-selected="true"] {{ color: {T['primary_light']} !important; border-bottom: 2px solid {T['primary']}; }}

    div[data-testid="stMetric"] {{
        background-color: {T['card']}; border: 1px solid {T['border']}; border-radius: 12px; padding: 14px 16px;
    }}
</style>
""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    paper_bgcolor=T["card"], plot_bgcolor=T["card"], font_color=T["text"],
    font_family="Inter", margin=dict(l=15, r=15, t=35, b=15),
    xaxis=dict(gridcolor=T["border"], zerolinecolor=T["border"]),
    yaxis=dict(gridcolor=T["border"], zerolinecolor=T["border"]),
)

# =========================================================
# SESIÓN HTTP "CAMUFLADA"
# =========================================================
def _get_yf_session():
    if _HAS_CURL_CFFI:
        try:
            return curl_requests.Session(impersonate="chrome")
        except Exception:
            return None
    return None

_YF_SESSION = _get_yf_session()

def _retry(fn, tries: int = 3, delay: float = 1.0):
    for _ in range(tries):
        try:
            res = fn()
            if res is not None and not (isinstance(res, pd.DataFrame) and res.empty):
                return res
        except Exception:
            pass
        time.sleep(delay)
    return None

# =========================================================
# EXTRACCIÓN Y CÁLCULO DE DATOS
# =========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_price_data(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    def _fetch():
        tk = yf.Ticker(ticker, session=_YF_SESSION) if _YF_SESSION else yf.Ticker(ticker)
        df = tk.history(period=period, interval=interval, auto_adjust=False)
        if df is None or df.empty:
            return None
        return df.dropna(subset=["Close"])
    df = _retry(_fetch)
    return df if df is not None else pd.DataFrame()

@st.cache_data(ttl=600, show_spinner=False)
def get_us02y() -> pd.DataFrame:
    """Obtiene rendimiento del Bono 2 años (US02Y) con fallbacks múltiples."""
    try:
        import pandas_datareader.data as web
        end = datetime.today()
        start = end - timedelta(days=400)
        df = web.DataReader("DGS2", "fred", start, end).dropna()
        if not df.empty:
            df.columns = ["Close"]
            return df
    except Exception:
        pass

    for sym in ["2YY=F", "^TNX", "^IRX"]:
        df = get_price_data(sym, period="1y")
        if not df.empty:
            return df[["Close"]]
    return pd.DataFrame()

# Indicadores Técnicos
def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def bollinger_bands(series: pd.Series, window: int = 20, num_sd: int = 2):
    sma = series.rolling(window).mean()
    std = series.rolling(window).std()
    upper = sma + (std * num_sd)
    lower = sma - (std * num_sd)
    return upper, sma, lower

# Tabla de Niveles Pivote (Clásicos y Camarilla)
def pivot_table(df: pd.DataFrame) -> tuple:
    if len(df) < 2:
        return pd.DataFrame(), 0.0
    last = df.iloc[-2]
    c_price = float(df.iloc[-1]["Close"])
    h, l, c = float(last["High"]), float(last["Low"]), float(last["Close"])
    
    pp = (h + l + c) / 3
    r1, s1 = 2 * pp - l, 2 * pp - h
    r2, s2 = pp + (h - l), pp - (h - l)
    r3, s3 = h + 2 * (pp - l), l - 2 * (h - pp)
    
    rng = h - l
    r4_cam = c + rng * 1.1 / 2
    s4_cam = c - rng * 1.1 / 2

    rows = [
        ("Resistencia R3", r3, "Resistencia"),
        ("Resistencia R4 (Camarilla Breakout)", r4_cam, "Resistencia"),
        ("Resistencia R2", r2, "Resistencia"),
        ("Resistencia R1", r1, "Resistencia"),
        ("Pivote Central (PP)", pp, "Pivote"),
        ("Soporte S1", s1, "Soporte"),
        ("Soporte S2", s2, "Soporte"),
        ("Soporte S4 (Camarilla Breakout)", s4_cam, "Soporte"),
        ("Soporte S3", s3, "Soporte"),
    ]
    dfp = pd.DataFrame(rows, columns=["Nivel", "Precio", "Tipo"]).sort_values("Precio", ascending=False)
    return dfp, c_price

def render_pivot_table(dfp: pd.DataFrame, ref_price: float):
    badge_cls = {"Resistencia": "cgb-badge-res", "Soporte": "cgb-badge-sop", "Pivote": "cgb-badge-piv"}
    rows_html = ""
    for _, row in dfp.iterrows():
        cls = badge_cls[row["Tipo"]]
        rows_html += f"""
        <tr>
            <td>{row['Nivel']}</td>
            <td style="font-weight:700;">${row['Precio']:,.2f}</td>
            <td><span class="cgb-badge {cls}">{row['Tipo'].upper()}</span></td>
        </tr>"""
    html = f"""
    <div class="cgb-label">Niveles Pivote Técnicos (Precio actual: ${ref_price:,.2f})</div>
    <table class="cgb-table">
        <thead><tr><th>Nivel</th><th>Precio</th><th>Tipo</th></tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    """
    st.markdown(html, unsafe_allow_html=True)

# COT (Commitments of Traders)
@st.cache_data(ttl=1800, show_spinner=False)
def get_cot_gold() -> pd.DataFrame:
    url = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
    params = {
        "$where": "cftc_contract_market_code='088691'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": 30,
    }
    def _fetch():
        r = requests.get(url, params=params, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        df = pd.DataFrame(r.json())
        if df.empty:
            return None
        for col in df.columns:
            if "positions" in col or "pct_of_oi" in col or col == "open_interest_all":
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["report_date_as_yyyy_mm_dd"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"])
        return df.sort_values("report_date_as_yyyy_mm_dd")
    df = _retry(_fetch, tries=2)
    return df if df is not None else pd.DataFrame()

# Opciones (Walls & Gamma Proxy) con filtro robusto ATM
@st.cache_data(ttl=1800, show_spinner=False)
def get_options_walls(tickers=("GLD", "IAU")):
    for ticker in tickers:
        try:
            tk = yf.Ticker(ticker, session=_YF_SESSION) if _YF_SESSION else yf.Ticker(ticker)
            exps = tk.options
            if not exps:
                continue
            hist = tk.history(period="5d")
            if hist.empty:
                continue
            spot_price = hist["Close"].iloc[-1]
            
            # Buscar en las primeras 3 fechas de vencimiento activas
            for exp in exps[:3]:
                chain = tk.option_chain(exp)
                calls = chain.calls.dropna(subset=["strike", "openInterest"])
                puts = chain.puts.dropna(subset=["strike", "openInterest"])
                if calls.empty and puts.empty:
                    continue
                
                # Filtrar strikes cerca del precio actual (+/- 12%)
                calls_f = calls[(calls["strike"] >= spot_price * 0.88) & (calls["strike"] <= spot_price * 1.12)]
                puts_f = puts[(puts["strike"] >= spot_price * 0.88) & (puts["strike"] <= spot_price * 1.12)]
                
                c_agg = calls_f.groupby("strike")["openInterest"].sum().reset_index()
                p_agg = puts_f.groupby("strike")["openInterest"].sum().reset_index()
                
                if c_agg["openInterest"].sum() > 0 or p_agg["openInterest"].sum() > 0:
                    return c_agg, p_agg, exp, ticker, spot_price
        except Exception:
            continue
    return pd.DataFrame(), pd.DataFrame(), None, None, None

# Noticias RSS
@st.cache_data(ttl=900, show_spinner=False)
def get_news():
    if not _HAS_FEEDPARSER:
        return []
    feeds = [
        "https://www.investing.com/rss/commodities_Gold.rss",
        "https://www.forexlive.com/feed/news",
    ]
    items = []
    for f in feeds:
        try:
            d = feedparser.parse(f)
            for e in d.entries[:6]:
                items.append({
                    "titulo": getattr(e, "title", ""),
                    "fecha": getattr(e, "published", ""),
                    "link": getattr(e, "link", "#"),
                })
        except Exception:
            continue
    return items[:12]

# =========================================================
# ALGORITMO CUANTITATIVO DE SESGO DIARIO
# =========================================================

def calcular_sesgo_cuantitativo(df_gold, df_dxy, df_us02y):
    señales = {}
    if not df_gold.empty and len(df_gold) > 20:
        close = df_gold["Close"].ffill()
        # 1. RSI (14)
        r = rsi(close).iloc[-1]
        if pd.notna(r):
            señales["RSI (14)"] = float(np.clip(r, 0, 100))
        
        # 2. Momentum Z-Score
        returns = close.pct_change()
        z_score = (returns.iloc[-1] - returns.rolling(20).mean().iloc[-1]) / (returns.rolling(20).std().iloc[-1] + 1e-6)
        señales["Z-Score Momentum"] = float(np.clip(50 + z_score * 20, 0, 100))
        
        # 3. Alineación EMA (20, 50)
        ema20, ema50 = ema(close, 20).iloc[-1], ema(close, 50).iloc[-1]
        señales["Tendencia (EMA 20/50)"] = 75 if close.iloc[-1] > ema20 > ema50 else (25 if close.iloc[-1] < ema20 < ema50 else 50)
        
        # 4. Volatilidad ATR
        atr_val = atr(df_gold).iloc[-1]
        if pd.notna(atr_val):
            atr_pct = (atr_val / close.iloc[-1]) * 100
            señales["Estabilidad (ATR)"] = float(np.clip(100 - atr_pct * 20, 0, 100))

    if not df_dxy.empty and len(df_dxy) > 5:
        dxy_close = df_dxy["Close"].ffill()
        dxy_mom = (dxy_close.iloc[-1] / dxy_close.iloc[-5] - 1) * 100
        señales["DXY (Inverso 5d)"] = float(np.clip(50 - dxy_mom * 10, 0, 100))

    if not df_us02y.empty and len(df_us02y) > 5:
        y = df_us02y.iloc[:, 0].ffill()
        y_mom = y.iloc[-1] - y.iloc[-5]
        señales["US02Y (Inverso 5d)"] = float(np.clip(50 - y_mom * 25, 0, 100))

    if not señales:
        return 50.0, "Sin datos", señales

    score = float(np.mean(list(señales.values())))
    etiqueta = "Sesgo Alcista" if score >= 62 else ("Sesgo Bajista" if score <= 38 else "Sesgo Neutral")
    return score, etiqueta, señales

def gauge_chart(score: float):
    color = T["bull"] if score >= 62 else (T["bear"] if score <= 38 else T["neutral"])
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        number={"font": {"size": 40, "color": T["text"]}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": T["muted"], "tickfont": {"color": T["muted"], "size": 10}},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": T["card"], "borderwidth": 0,
            "steps": [
                {"range": [0, 38], "color": "rgba(255,90,103,0.15)"},
                {"range": [38, 62], "color": "rgba(232,199,102,0.15)"},
                {"range": [62, 100], "color": "rgba(47,213,131,0.15)"},
            ],
        },
    ))
    fig.update_layout(height=230, margin=dict(l=20, r=20, t=10, b=10), **PLOTLY_LAYOUT)
    return fig

# =========================================================
# CABECERA Y CONTROL SIDEBAR
# =========================================================
st.markdown(f"""
<div class="cgb-header">
    <div class="cgb-logo">CGB</div>
    <div>
        <p class="cgb-title">CGB COMUNITY — Terminal XAU/USD</p>
        <p class="cgb-subtitle">Análisis cuantitativo del Oro combinando datos macro, COT, opciones, estructura técnica y correlaciones</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Filtros Globales en Sidebar
st.sidebar.markdown("### ⚙️ Parámetros de Análisis")
period_choice = st.sidebar.select_slider("Ventana Temporal (Gráficos):", options=["3mo", "6mo", "1y", "2y"], value="1y")

if st.sidebar.button("🔄 Actualizar Datos en Vivo"):
    st.cache_data.clear()
    st.rerun()

# Cargar Datos Principal
with st.spinner("Cargando terminal de mercado..."):
    df_gold = get_price_data("GC=F", period=period_choice)
    df_dxy = get_price_data("DX-Y.NYB", period=period_choice)
    if df_dxy.empty:
        df_dxy = get_price_data("DX=F", period=period_choice)
    df_us02y = get_us02y()

# Pestañas Principales
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🎯 Resumen y Sesgo", "🥇 Oro (XAU/USD)", "🌐 Macro y Correlación",
    "🏛️ Posicionamiento COT", "🛡️ Muros de Opciones", "🧮 Calculadora Riesgo", "📰 Noticias"
])

# =========================================================
# TAB 1: RESUMEN Y SESGO DIARIO
# =========================================================
with tab1:
    score, etiqueta, señales = calcular_sesgo_cuantitativo(df_gold, df_dxy, df_us02y)
    cls_tag = "cgb-bull" if score >= 62 else ("cgb-bear" if score <= 38 else "cgb-neutral")

    c1, c2 = st.columns([1, 1.4])
    with c1:
        with st.container():
            st.markdown('<div class="cgb-label" style="text-align:center;">Score CGB Cuantitativo</div>', unsafe_allow_html=True)
            st.plotly_chart(gauge_chart(score), use_container_width=True, config={"displayModeBar": False})
            st.markdown(f'<div class="{cls_tag}" style="text-align:center; font-size:1.4rem; font-weight:800;">{etiqueta}</div>', unsafe_allow_html=True)

    with c2:
        with st.container():
            st.markdown('<div class="cgb-label">Desglose de Componentes de Sesgo</div>', unsafe_allow_html=True)
            if señales:
                fig_bar = go.Figure(go.Bar(
                    x=list(señales.values()), y=list(señales.keys()), orientation="h",
                    marker_color=[T["bull"] if v >= 55 else (T["bear"] if v <= 45 else T["neutral"]) for v in señales.values()],
                    text=[f"{v:.0f}" for v in señales.values()], textposition="outside",
                ))
                fig_bar.update_layout(xaxis_range=[0, 105], height=260, **PLOTLY_LAYOUT)
                st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    # Métricas Clave Principales
    m1, m2, m3 = st.columns(3)
    if not df_gold.empty:
        p_gold = df_gold["Close"].iloc[-1]
        v_gold = (df_gold["Close"].iloc[-1] / df_gold["Close"].iloc[-2] - 1) * 100 if len(df_gold) > 1 else 0
        m1.metric("Oro Spot (GC=F)", f"${p_gold:,.2f}", f"{v_gold:+.2f}%")
    else:
        m1.metric("Oro Spot (GC=F)", "—")

    if not df_dxy.empty:
        p_dxy = df_dxy["Close"].iloc[-1]
        v_dxy = (df_dxy["Close"].iloc[-1] / df_dxy["Close"].iloc[-2] - 1) * 100 if len(df_dxy) > 1 else 0
        m2.metric("Índice Dólar (DXY)", f"{p_dxy:,.2f}", f"{v_dxy:+.2f}%")
    else:
        m2.metric("Índice Dólar (DXY)", "—")

    if not df_us02y.empty:
        p_y = df_us02y.iloc[-1, 0]
        p_y_prev = df_us02y.iloc[-2, 0] if len(df_us02y) > 1 else p_y
        m3.metric("Rendimiento US02Y", f"{p_y:.2f}%", f"{(p_y - p_y_prev):+.2f} pts")
    else:
        m3.metric("Rendimiento US02Y", "—")

    # Pivotes Técnicos
    if not df_gold.empty:
        st.markdown("---")
        dfp, ref_price = pivot_table(df_gold)
        render_pivot_table(dfp, ref_price)

# =========================================================
# TAB 2: ORO (XAU/USD) - ANÁLISIS TÉCNICO COMPLETO
# =========================================================
with tab2:
    if df_gold.empty:
        st.warning("No hay datos disponibles para el Oro en este momento.")
    else:
        df = df_gold.copy()
        df["EMA20"] = ema(df["Close"], 20)
        df["EMA50"] = ema(df["Close"], 50)
        df["EMA200"] = ema(df["Close"], 200)
        df["B_Upper"], df["B_Mid"], df["B_Lower"] = bollinger_bands(df["Close"])
        df["RSI14"] = rsi(df["Close"], 14)
        df["ATR14"] = atr(df, 14)

        # Gráfico principal con subplots (Velas + RSI)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.75, 0.25])
        
        # Velas y Medias Móviles
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
            name="XAU/USD", increasing_line_color=T["bull"], decreasing_line_color=T["bear"]
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA20"], line=dict(color=T["primary_light"], width=1.5), name="EMA 20"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], line=dict(color=T["blue"], width=1.5), name="EMA 50"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA200"], line=dict(color=T["muted"], width=1.5), name="EMA 200"), row=1, col=1)
        
        # Bandas de Bollinger
        fig.add_trace(go.Scatter(x=df.index, y=df["B_Upper"], line=dict(color="rgba(150,150,150,0.3)", dash="dash"), name="Bollinger Sup"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["B_Lower"], line=dict(color="rgba(150,150,150,0.3)", dash="dash"), name="Bollinger Inf"), row=1, col=1)

        # RSI Subplot
        fig.add_trace(go.Scatter(x=df.index, y=df["RSI14"], line=dict(color=T["primary_light"], width=1.5), name="RSI (14)"), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color=T["bear"], row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color=T["bull"], row=2, col=1)

        fig.update_layout(height=600, xaxis_rangeslider_visible=False, **PLOTLY_LAYOUT)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        col_a, col_b = st.columns(2)
        with col_a:
            fig_vol = go.Figure(go.Bar(x=df.index, y=df["Volume"], marker_color=T["blue"]))
            fig_vol.update_layout(title="Volumen Negociado", height=240, **PLOTLY_LAYOUT)
            st.plotly_chart(fig_vol, use_container_width=True, config={"displayModeBar": False})
        with col_b:
            fig_atr = go.Figure(go.Scatter(x=df.index, y=df["ATR14"], line=dict(color=T["bear"], width=2)))
            fig_atr.update_layout(title="ATR (14) — Volatilidad Diaria ($)", height=240, **PLOTLY_LAYOUT)
            st.plotly_chart(fig_atr, use_container_width=True, config={"displayModeBar": False})

# =========================================================
# TAB 3: MACRO & CORRELACIÓN CUANTITATIVA
# =========================================================
with tab3:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="cgb-label">Índice del Dólar (DXY)</div>', unsafe_allow_html=True)
        if not df_dxy.empty:
            fig = go.Figure(go.Candlestick(
                x=df_dxy.index, open=df_dxy["Open"], high=df_dxy["High"], low=df_dxy["Low"], close=df_dxy["Close"],
                increasing_line_color=T["bull"], decreasing_line_color=T["bear"], name="DXY"
            ))
            fig.update_layout(height=350, xaxis_rangeslider_visible=False, **PLOTLY_LAYOUT)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.markdown('<div class="cgb-label">Rendimiento Bono USA 2A (US02Y)</div>', unsafe_allow_html=True)
        if not df_us02y.empty:
            fig = go.Figure(go.Scatter(
                x=df_us02y.index, y=df_us02y.iloc[:, 0], line=dict(color=T["primary_light"], width=2),
                fill="tozeroy", fillcolor="rgba(201,162,39,0.08)"
            ))
            fig.update_layout(height=350, **PLOTLY_LAYOUT)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # CORRELACIÓN MÓVIL CUANTITATIVA (ROLLING CORRELATION)
    st.markdown("---")
    st.markdown('<div class="cgb-label">Matriz de Correlación Móvil a 30 días (Pearson)</div>', unsafe_allow_html=True)
    
    if not df_gold.empty and not df_dxy.empty:
        df_corr = pd.DataFrame({
            "Gold": df_gold["Close"].pct_change(),
            "DXY": df_dxy["Close"].pct_change()
        }).dropna()
        
        rolling_corr = df_corr["Gold"].rolling(30).corr(df_corr["DXY"]).dropna()
        
        fig_corr = go.Figure()
        fig_corr.add_trace(go.Scatter(x=rolling_corr.index, y=rolling_corr, line=dict(color=T["blue"], width=2), name="Corr 30d (Oro vs DXY)"))
        fig_corr.add_hline(y=0, line_dash="dash", line_color=T["muted"])
        fig_corr.update_layout(height=260, yaxis_range=[-1, 1], **PLOTLY_LAYOUT)
        st.plotly_chart(fig_corr, use_container_width=True, config={"displayModeBar": False})
        st.caption("Una correlación cercana a -1 indica una fuerte relación inversa histórica entre el Dólar y el Oro.")

# =========================================================
# TAB 4: POSICIONAMIENTO INSTITUCIONAL (COT)
# =========================================================
with tab4:
    df_cot = get_cot_gold()
    if df_cot.empty:
        st.warning("No se pudieron consultar los informes de la CFTC en este momento.")
    else:
        last_cot = df_cot.iloc[-1]
        fecha_str = last_cot["report_date_as_yyyy_mm_dd"].strftime("%d/%m/%Y")
        
        st.markdown(f'<div class="cgb-label">Informe Commitments of Traders (COT) — COMEX Oro · Fecha: {fecha_str}</div>', unsafe_allow_html=True)
        
        # Tabla resumen COT
        col_cot1, col_cot2, col_cot3 = st.columns(3)
        
        com_net = last_cot.get("comm_positions_long_all", 0) - last_cot.get("comm_positions_short_all", 0)
        noncom_net = last_cot.get("noncomm_positions_long_all", 0) - last_cot.get("noncomm_positions_short_all", 0)
        small_net = last_cot.get("nonrept_positions_long_all", 0) - last_cot.get("nonrept_positions_short_all", 0)
        
        col_cot1.metric("Comerciales (Hedgers)", f"{com_net:+,.0f}", "Posición Neta")
        col_cot2.metric("Grandes Especuladores (Fondos)", f"{noncom_net:+,.0f}", "Posición Neta")
        col_cot3.metric("Pequeños Traders", f"{small_net:+,.0f}", "Posición Neta")

        # Gráfico evolutivo COT
        fig_cot = go.Figure()
        fig_cot.add_trace(go.Scatter(x=df_cot["report_date_as_yyyy_mm_dd"], y=df_cot["noncomm_positions_long_all"], name="Grandes Esp. — Largos", line=dict(color=T["bull"])))
        fig_cot.add_trace(go.Scatter(x=df_cot["report_date_as_yyyy_mm_dd"], y=df_cot["noncomm_positions_short_all"], name="Grandes Esp. — Cortos", line=dict(color=T["bear"])))
        fig_cot.add_trace(go.Scatter(x=df_cot["report_date_as_yyyy_mm_dd"], y=df_cot["comm_positions_long_all"], name="Comerciales — Largos", line=dict(color=T["blue"], dash="dot")))
        
        fig_cot.update_layout(height=380, title="Evolución Histórica de Contratos", **PLOTLY_LAYOUT)
        st.plotly_chart(fig_cot, use_container_width=True, config={"displayModeBar": False})

# =========================================================
# TAB 5: MUROS DE OPCIONES & OPEN INTEREST
# =========================================================
with tab5:
    st.markdown('<div class="cgb-label">Muros de Open Interest (Opciones ETF GLD - Proxy de Plataforma Institutional)</div>', unsafe_allow_html=True)
    calls, puts, exp, ticker_used, spot_etf = get_options_walls()
    
    if calls.empty and puts.empty:
        st.info("No hay datos de volumen de opciones disponibles o el mercado está cerrado.")
    else:
        st.caption(f"Activo Proxy: **{ticker_used}** | Vencimiento: **{exp}** | Precio ETF Spot: **${spot_etf:.2f}**")
        
        fig_opt = go.Figure()
        fig_opt.add_trace(go.Bar(x=calls["strike"], y=calls["openInterest"], name="Calls (Resistencias)", marker_color=T["bull"]))
        fig_opt.add_trace(go.Bar(x=puts["strike"], y=puts["openInterest"], name="Puts (Soportes)", marker_color=T["bear"]))
        
        fig_opt.update_layout(height=420, barmode="group", xaxis_title="Strike Price ($)", yaxis_title="Open Interest (Contratos)", **PLOTLY_LAYOUT)
        st.plotly_chart(fig_opt, use_container_width=True, config={"displayModeBar": False})

# =========================================================
# TAB 6: CALCULADORA CUANTITATIVA DE GESTIÓN DE RIESGO
# =========================================================
with tab6:
    st.markdown('<div class="cgb-label">Calculadora Cuantitativa de Tamaño de Posición (XAU/USD)</div>', unsafe_allow_html=True)
    
    rc1, rc2, rc3 = st.columns(3)
    balance = rc1.number_input("Balance de la Cuenta ($):", min_value=100.0, value=10000.0, step=500.0)
    risk_pct = rc2.number_input("Riesgo por Operación (%):", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
    entry_price = rc3.number_input("Precio de Entrada ($):", min_value=100.0, value=float(df_gold["Close"].iloc[-1]) if not df_gold.empty else 2500.0)

    rc4, rc5 = st.columns(2)
    sl_price = rc4.number_input("Stop Loss ($):", min_value=100.0, value=entry_price - 15.0)
    tp_price = rc5.number_input("Take Profit ($):", min_value=100.0, value=entry_price + 30.0)

    # Cálculos Cuantitativos de Riesgo
    risk_amount = balance * (risk_pct / 100.0)
    sl_distance = abs(entry_price - sl_price)
    tp_distance = abs(tp_price - entry_price)
    
    if sl_distance > 0:
        # En XAU/USD: 1 Lote Estándar = 100 onzas ($1 de movimiento = $100 por lote)
        lot_size = risk_amount / (sl_distance * 100.0)
        rr_ratio = tp_distance / sl_distance
        profit_amount = lot_size * tp_distance * 100.0

        st.markdown("---")
        res1, res2, res3, res4 = st.columns(4)
        res1.metric("Lotaje Sugerido", f"{lot_size:.2f} Lotes")
        res2.metric("Riesgo Máximo", f"${risk_amount:,.2f}")
        res3.metric("Beneficio Potencial", f"${profit_amount:,.2f}")
        res4.metric("Ratio Riesgo / Beneficio", f"1 : {rr_ratio:.2f}")
    else:
        st.error("El Stop Loss debe ser diferente al Precio de Entrada.")

# =========================================================
# TAB 7: NOTICIAS
# =========================================================
with tab7:
    st.markdown('<div class="cgb-label">Últimas Noticias de Mercado (Commodities & Macro)</div>', unsafe_allow_html=True)
    noticias = get_news()
    if not noticias:
        st.info("No se pudieron cargar noticias recientes vía RSS o la librería 'feedparser' no está disponible.")
    else:
        for n in noticias:
            st.markdown(f"""
            <div class="cgb-news-card">
                <a href="{n['link']}" target="_blank" class="cgb-news-title">{n['titulo']}</a>
                <div class="cgb-news-meta">{n['fecha']}</div>
            </div>
            """, unsafe_allow_html=True)

# Footer Informativo
st.markdown(f'<div class="cgb-footer" style="text-align:center; padding:20px; color:{T["muted"]}; font-size:0.8rem;">CGB COMUNITY — Terminal Cuantitativo de Análisis. Los datos son puramente informativos y educativos. No representan una recomendación financiera.</div>', unsafe_allow_html=True)
