# -*- coding: utf-8 -*-
"""
CGB COMUNITY - Terminal XAU/USD
--------------------------------
App gratuita (Streamlit) para analizar el posible sesgo diario del oro (XAU/USD)
combinando: Oro (GC=F), Dólar (DXY), Bono USA 2 años (US02Y), ATR, EMAs, volumen,
posicionamiento COT, muros del mercado de opciones (Open Interest) y noticias.

NOTA IMPORTANTE: Esta herramienta es solo informativa/educativa. No constituye
asesoramiento financiero ni una recomendación de inversión.
"""

import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

try:
    from curl_cffi import requests as curl_requests
    _HAS_CURL_CFFI = True
except Exception:
    _HAS_CURL_CFFI = False

# =========================================================
# CONFIGURACIÓN GENERAL DE LA PÁGINA
# =========================================================
st.set_page_config(
    page_title="CGB COMUNITY | Terminal XAU/USD",
    page_icon="🥇",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PRIMARY = "#c9a227"
PRIMARY_LIGHT = "#e8c766"
BG = "#0a0c10"
CARD = "#12151c"
BORDER = "#232733"
TEXT = "#eef0f3"
MUTED = "#8b93a3"
BULL = "#2fd583"
BEAR = "#ff5a67"
NEUTRAL = "#e8c766"
BLUE = "#4da6ff"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background-color: {BG}; }}
    #MainMenu, footer {{visibility: hidden;}}
    section[data-testid="stSidebar"] {{ background-color: {CARD}; }}

    .cgb-header {{
        display: flex; align-items: center; gap: 16px;
        padding: 22px 26px; margin-bottom: 18px;
        background: linear-gradient(135deg, #12151c 0%, #191c26 100%);
        border: 1px solid {BORDER}; border-radius: 14px;
    }}
    .cgb-logo {{
        width: 46px; height: 46px; border-radius: 10px;
        background: linear-gradient(135deg, {PRIMARY} 0%, {PRIMARY_LIGHT} 100%);
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 1.1rem; color: #12151c; flex-shrink: 0;
    }}
    .cgb-title {{ font-size: 1.5rem; font-weight: 800; color: {TEXT}; letter-spacing: -0.02em; margin: 0; }}
    .cgb-subtitle {{ color: {MUTED}; font-size: 0.85rem; margin-top: 2px; }}

    .cgb-label {{ color: {MUTED}; font-size: 0.72rem; text-transform: uppercase; letter-spacing: .08em; font-weight: 700; margin-bottom: 10px; }}
    .cgb-bull {{ color: {BULL}; }}
    .cgb-bear {{ color: {BEAR}; }}
    .cgb-neutral {{ color: {NEUTRAL}; }}

    .cgb-news-card {{
        background-color: {CARD}; border: 1px solid {BORDER}; border-radius: 12px;
        padding: 14px 16px; margin-bottom: 10px; transition: border-color .15s;
    }}
    .cgb-news-card:hover {{ border-color: {PRIMARY}; }}
    .cgb-news-title {{ color: {TEXT}; text-decoration: none; font-weight: 600; font-size: 0.95rem; }}
    .cgb-news-meta {{ color: {MUTED}; font-size: 0.72rem; margin-top: 6px; }}

    .cgb-footer {{ color: {MUTED}; font-size: 0.78rem; text-align: center; padding: 24px 0 10px 0; }}

    .cgb-table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
    .cgb-table th {{
        text-align: left; color: {MUTED}; font-size: 0.7rem; text-transform: uppercase;
        letter-spacing: .06em; padding: 8px 10px; border-bottom: 1px solid {BORDER}; font-weight: 700;
    }}
    .cgb-table td {{ padding: 10px; border-bottom: 1px solid {BORDER}; color: {TEXT}; }}
    .cgb-table tr:last-child td {{ border-bottom: none; }}
    .cgb-badge {{
        display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.72rem;
        font-weight: 700; letter-spacing: .03em;
    }}
    .cgb-badge-res {{ background: rgba(255,90,103,0.15); color: {BEAR}; border: 1px solid rgba(255,90,103,0.35); }}
    .cgb-badge-sop {{ background: rgba(47,213,131,0.15); color: {BULL}; border: 1px solid rgba(47,213,131,0.35); }}
    .cgb-badge-piv {{ background: rgba(232,199,102,0.15); color: {NEUTRAL}; border: 1px solid rgba(232,199,102,0.35); }}

    .stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {BORDER}; }}
    .stTabs [data-baseweb="tab"] {{
        background-color: transparent; border-radius: 8px 8px 0 0; padding: 10px 16px;
        color: {MUTED}; font-weight: 600;
    }}
    .stTabs [aria-selected="true"] {{ color: {PRIMARY_LIGHT} !important; border-bottom: 2px solid {PRIMARY}; }}

    div[data-testid="stMetric"] {{
        background-color: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; padding: 14px 16px;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 14px !important; border-color: {BORDER} !important; background-color: {CARD} !important;
    }}
</style>
""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    paper_bgcolor=CARD, plot_bgcolor=CARD, font_color=TEXT,
    font_family="Inter", margin=dict(l=10, r=10, t=30, b=10),
)

# =========================================================
# SESIÓN HTTP "camuflada" para evitar bloqueos de Yahoo Finance
# =========================================================
def _get_yf_session():
    if _HAS_CURL_CFFI:
        try:
            return curl_requests.Session(impersonate="chrome")
        except Exception:
            return None
    return None

_YF_SESSION = _get_yf_session()


def _retry(fn, tries: int = 3, delay: float = 1.2):
    for _ in range(tries):
        try:
            result = fn()
            if result is not None and not (isinstance(result, pd.DataFrame) and result.empty):
                return result
        except Exception:
            pass
        time.sleep(delay)
    return None


# =========================================================
# FUNCIONES DE DATOS
# =========================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_price_data(ticker: str, period: str = "9mo", interval: str = "1d") -> pd.DataFrame:
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
    def _fetch():
        import pandas_datareader.data as web
        end = datetime.today()
        start = end - timedelta(days=400)
        df = web.DataReader("DGS2", "fred", start, end)
        return df.dropna()
    df = _retry(_fetch, tries=2)
    return df if df is not None else pd.DataFrame()


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


def pivot_table(df: pd.DataFrame) -> tuple:
    """Pivotes clásicos + niveles Camarilla (breakout), ordenados de mayor a menor precio."""
    last = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
    h, l, c = float(last["High"]), float(last["Low"]), float(last["Close"])
    pp = (h + l + c) / 3
    r1, s1 = 2 * pp - l, 2 * pp - h
    r2, s2 = pp + (h - l), pp - (h - l)
    r3, s3 = h + 2 * (pp - l), l - 2 * (h - pp)
    rng = h - l
    r4 = c + rng * 1.1 / 2
    s4 = c - rng * 1.1 / 2

    rows = [
        ("R3", r3, "Resistencia"),
        ("R2", r2, "Resistencia"),
        ("R1", r1, "Resistencia"),
        ("R4 (Camarilla)", r4, "Resistencia"),
        ("PP (Pivote)", pp, "Pivote"),
        ("S1", s1, "Soporte"),
        ("S4 (Camarilla)", s4, "Soporte"),
        ("S2", s2, "Soporte"),
        ("S3", s3, "Soporte"),
    ]
    dfp = pd.DataFrame(rows, columns=["Nivel", "Precio", "Tipo"]).sort_values("Precio", ascending=False)
    return dfp, c


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
    <div class="cgb-label">Pivotes técnicos (ref: ${ref_price:,.2f})</div>
    <table class="cgb-table">
        <thead><tr><th>Nivel</th><th>Precio</th><th>Tipo</th></tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    """
    st.markdown(html, unsafe_allow_html=True)


@st.cache_data(ttl=1800, show_spinner=False)
def get_cot_gold() -> pd.DataFrame:
    """
    Informe COT (CFTC) semanal, filtrado ÚNICAMENTE al contrato estándar de Oro
    (COMEX, código 088691) para evitar mezclar datos con Micro Gold u otros
    contratos, que era la causa del gráfico en 'zigzag'.
    """
    url = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
    params = {
        "$where": "cftc_contract_market_code='088691'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": 30,
    }

    def _fetch():
        r = requests.get(url, params=params, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        df = pd.DataFrame(r.json())
        if df.empty:
            return None
        for c in df.columns:
            if c in ("market_and_exchange_names", "report_date_as_yyyy_mm_dd", "yyyy_report_week_ww",
                      "contract_market_name", "cftc_contract_market_code", "cftc_market_code",
                      "cftc_region_code", "cftc_commodity_code"):
                continue
            converted = pd.to_numeric(df[c], errors="coerce")
            if converted.notna().sum() > 0:
                df[c] = converted
        df["report_date_as_yyyy_mm_dd"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"])
        return df.sort_values("report_date_as_yyyy_mm_dd")

    df = _retry(_fetch, tries=2)
    return df if df is not None else pd.DataFrame()


def render_cot_table(row: pd.Series):
    """Tabla estilo 'Legacy Report' — Comerciales / Grandes Especuladores / Pequeños Traders."""
    def g(col):
        return row[col] if col in row.index and pd.notna(row[col]) else 0

    categorias = [
        ("Comerciales", "comm_positions_long_all", "comm_positions_short_all",
         "pct_of_oi_comm_long_all", "pct_of_oi_comm_short_all"),
        ("Grandes especuladores", "noncomm_positions_long_all", "noncomm_positions_short_all",
         "pct_of_oi_noncomm_long_all", "pct_of_oi_noncomm_short_all"),
        ("Pequeños traders", "nonrept_positions_long_all", "nonrept_positions_short_all",
         "pct_of_oi_nonrept_long_all", "pct_of_oi_nonrept_short_all"),
    ]

    rows_html = ""
    for nombre, long_col, short_col, pctl_col, pcts_col in categorias:
        long_v, short_v = g(long_col), g(short_col)
        neto = long_v - short_v
        neto_cls = "cgb-bull" if neto > 0 else ("cgb-bear" if neto < 0 else "")
        pctl, pcts = g(pctl_col), g(pcts_col)
        rows_html += f"""
        <tr>
            <td style="font-weight:600;">{nombre}</td>
            <td>{long_v:,.0f}</td>
            <td>{short_v:,.0f}</td>
            <td class="{neto_cls}" style="font-weight:700;">{neto:+,.0f}</td>
            <td>{pctl:.1f}%</td>
            <td>{pcts:.1f}%</td>
        </tr>"""

    oi = g("open_interest_all")
    fecha = row["report_date_as_yyyy_mm_dd"].strftime("%d/%m/%Y") if "report_date_as_yyyy_mm_dd" in row.index else ""

    html = f"""
    <div class="cgb-label">Commitments of Traders — Oro (COMEX, contrato estándar) · Informe del {fecha}</div>
    <table class="cgb-table">
        <thead>
            <tr><th>Categoría</th><th>Largos</th><th>Cortos</th><th>Neto</th><th>% OI Largos</th><th>% OI Cortos</th></tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>
    <div style="margin-top:12px; color:{MUTED}; font-size:0.8rem;">Open Interest total: <b style="color:{TEXT};">{oi:,.0f}</b> contratos</div>
    """
    st.markdown(html, unsafe_allow_html=True)


@st.cache_data(ttl=1800, show_spinner=False)
def get_options_walls(tickers=("GLD", "IAU")):
    for ticker in tickers:
        try:
            tk = yf.Ticker(ticker, session=_YF_SESSION) if _YF_SESSION else yf.Ticker(ticker)
            exps = tk.options
            if not exps:
                continue
            exp = exps[0]
            chain = tk.option_chain(exp)
            calls = chain.calls[["strike", "openInterest", "volume"]].groupby("strike").sum().reset_index()
            puts = chain.puts[["strike", "openInterest", "volume"]].groupby("strike").sum().reset_index()
            if not calls.empty or not puts.empty:
                return calls, puts, exp, ticker
        except Exception:
            continue
    return pd.DataFrame(), pd.DataFrame(), None, None


@st.cache_data(ttl=900, show_spinner=False)
def get_news():
    feeds = [
        "https://www.investing.com/rss/commodities_Gold.rss",
        "https://www.investing.com/rss/news_285.rss",
        "https://www.forexlive.com/feed/news",
    ]
    items = []
    for f in feeds:
        try:
            import feedparser
            d = feedparser.parse(f)
            for e in d.entries[:8]:
                items.append({
                    "titulo": getattr(e, "title", ""),
                    "fecha": getattr(e, "published", ""),
                    "link": getattr(e, "link", "#"),
                })
        except Exception:
            continue
    return items[:15]


# =========================================================
# CÁLCULO DEL SESGO DEL DÍA
# =========================================================

def calcular_sesgo(df_gold, df_dxy, df_us02y):
    señales = {}
    if not df_gold.empty and len(df_gold) > 20:
        close = df_gold["Close"]
        r = rsi(close).iloc[-1]
        if pd.notna(r):
            señales["RSI (14)"] = float(np.clip(r, 0, 100))
        mom20 = (close.iloc[-1] / close.iloc[-20] - 1) * 100
        señales["Momentum 20d"] = float(np.clip(50 + mom20 * 4, 0, 100))
        ema20, ema50 = ema(close, 20).iloc[-1], ema(close, 50).iloc[-1]
        tendencia = 70 if close.iloc[-1] > ema20 > ema50 else (30 if close.iloc[-1] < ema20 < ema50 else 50)
        señales["Tendencia (EMA)"] = tendencia
        atr_val = atr(df_gold).iloc[-1]
        if pd.notna(atr_val):
            atr_pct = (atr_val / close.iloc[-1]) * 100
            señales["Estabilidad (ATR)"] = float(np.clip(100 - atr_pct * 25, 0, 100))

    if not df_dxy.empty and len(df_dxy) > 6:
        dxy_close = df_dxy["Close"]
        dxy_mom = (dxy_close.iloc[-1] / dxy_close.iloc[-6] - 1) * 100
        señales["DXY (inverso)"] = float(np.clip(50 - dxy_mom * 8, 0, 100))

    if not df_us02y.empty and len(df_us02y) > 6:
        y = df_us02y.iloc[:, 0]
        y_mom = y.iloc[-1] - y.iloc[-6]
        señales["US02Y (inverso)"] = float(np.clip(50 - y_mom * 20, 0, 100))

    if not señales:
        return 50, "Sin datos suficientes", señales

    score = float(np.mean(list(señales.values())))
    etiqueta = "Sesgo Alcista" if score >= 65 else ("Sesgo Bajista" if score <= 35 else "Sesgo Neutral")
    return score, etiqueta, señales


def gauge_chart(score: float):
    color = BULL if score >= 65 else (BEAR if score <= 35 else NEUTRAL)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        number={"font": {"size": 42, "color": TEXT}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": MUTED, "tickfont": {"color": MUTED, "size": 10}},
            "bar": {"color": color, "thickness": 0.28},
            "bgcolor": CARD, "borderwidth": 0,
            "steps": [
                {"range": [0, 35], "color": "#2a1418"},
                {"range": [35, 65], "color": "#2a2618"},
                {"range": [65, 100], "color": "#12261c"},
            ],
        },
    ))
    fig.update_layout(height=230, margin=dict(l=20, r=20, t=10, b=10),
                       paper_bgcolor=CARD, plot_bgcolor=CARD, font_color=TEXT, font_family="Inter")
    return fig


# =========================================================
# CABECERA
# =========================================================
st.markdown(f"""
<div class="cgb-header">
    <div class="cgb-logo">CGB</div>
    <div>
        <p class="cgb-title">CGB COMUNITY — Terminal XAU/USD</p>
        <p class="cgb-subtitle">Sesgo diario del oro combinando GC, DXY, US02Y, ATR, EMA, volumen, COT, muros de opciones y noticias · uso educativo</p>
    </div>
</div>
""", unsafe_allow_html=True)

with st.spinner("Cargando datos de mercado..."):
    df_gold = get_price_data("GC=F")
    df_dxy = get_price_data("DX-Y.NYB")
    if df_dxy.empty:
        df_dxy = get_price_data("DX=F")
    df_us02y = get_us02y()

tab_resumen, tab_oro, tab_macro, tab_cot, tab_opciones, tab_noticias = st.tabs(
    ["Resumen del día", "Oro (XAU/USD)", "DXY & US02Y", "COT", "Muros de opciones", "Noticias"]
)

# =========================================================
# TAB: RESUMEN DEL DÍA
# =========================================================
with tab_resumen:
    score, etiqueta, señales = calcular_sesgo(df_gold, df_dxy, df_us02y)
    color_clase = "cgb-bull" if score >= 65 else ("cgb-bear" if score <= 35 else "cgb-neutral")

    col1, col2 = st.columns([1, 1.4])
    with col1:
        with st.container(border=True):
            st.markdown('<div class="cgb-label" style="text-align:center;">Score CGB del día</div>', unsafe_allow_html=True)
            st.plotly_chart(gauge_chart(score), use_container_width=True, config={"displayModeBar": False})
            st.markdown(f'<div class="{color_clase}" style="text-align:center; font-size:1.3rem; font-weight:700;">{etiqueta}</div>', unsafe_allow_html=True)

    with col2:
        with st.container(border=True):
            st.markdown('<div class="cgb-label">Desglose de señales</div>', unsafe_allow_html=True)
            if señales:
                fig = go.Figure(go.Bar(
                    x=list(señales.values()), y=list(señales.keys()), orientation="h",
                    marker_color=[BULL if v >= 55 else (BEAR if v <= 45 else NEUTRAL) for v in señales.values()],
                    text=[f"{v:.0f}" for v in señales.values()], textposition="outside",
                ))
                fig.update_layout(xaxis_range=[0, 105], height=260, **PLOTLY_LAYOUT)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("Sin señales suficientes todavía.")

    c1, c2, c3 = st.columns(3)
    if not df_gold.empty:
        precio = df_gold["Close"].iloc[-1]
        var = (df_gold["Close"].iloc[-1] / df_gold["Close"].iloc[-2] - 1) * 100 if len(df_gold) > 1 else 0
        c1.metric("Oro (GC=F)", f"${precio:,.2f}", f"{var:+.2f}%")
    else:
        c1.metric("Oro (GC=F)", "—")
    if not df_dxy.empty:
        dxy_val = df_dxy["Close"].iloc[-1]
        dxy_var = (df_dxy["Close"].iloc[-1] / df_dxy["Close"].iloc[-2] - 1) * 100 if len(df_dxy) > 1 else 0
        c2.metric("DXY", f"{dxy_val:,.2f}", f"{dxy_var:+.2f}%")
    else:
        c2.metric("DXY", "—")
    if not df_us02y.empty:
        y_val = df_us02y.iloc[-1, 0]
        y_prev = df_us02y.iloc[-2, 0] if len(df_us02y) > 1 else y_val
        c3.metric("US 2Y Yield", f"{y_val:.2f}%", f"{(y_val - y_prev):+.2f} pts")
    else:
        c3.metric("US 2Y Yield", "—")

    if not df_gold.empty:
        with st.container(border=True):
            dfp, ref_price = pivot_table(df_gold)
            render_pivot_table(dfp, ref_price)

# =========================================================
# TAB: ORO
# =========================================================
with tab_oro:
    if df_gold.empty:
        st.warning("No se pudieron cargar los datos del oro en este momento. Prueba a recargar en unos segundos.")
    else:
        df = df_gold.copy()
        df["EMA20"] = ema(df["Close"], 20)
        df["EMA50"] = ema(df["Close"], 50)
        df["EMA200"] = ema(df["Close"], 200)
        df["ATR14"] = atr(df, 14)
        df["RSI14"] = rsi(df["Close"], 14)

        with st.container(border=True):
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
                name="XAU/USD", increasing_line_color=BULL, decreasing_line_color=BEAR,
            ))
            fig.add_trace(go.Scatter(x=df.index, y=df["EMA20"], line=dict(color=PRIMARY_LIGHT, width=1), name="EMA 20"))
            fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], line=dict(color=BLUE, width=1), name="EMA 50"))
            fig.add_trace(go.Scatter(x=df.index, y=df["EMA200"], line=dict(color=MUTED, width=1), name="EMA 200"))
            fig.update_layout(height=500, xaxis_rangeslider_visible=False, **PLOTLY_LAYOUT)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                fig_vol = go.Figure(go.Bar(x=df.index, y=df["Volume"], marker_color=BLUE))
                fig_vol.update_layout(title="Volumen", height=250, **PLOTLY_LAYOUT)
                st.plotly_chart(fig_vol, use_container_width=True, config={"displayModeBar": False})
        with c2:
            with st.container(border=True):
                fig_atr = go.Figure(go.Scatter(x=df.index, y=df["ATR14"], line=dict(color=BEAR)))
                fig_atr.update_layout(title="ATR (14) — Volatilidad", height=250, **PLOTLY_LAYOUT)
                st.plotly_chart(fig_atr, use_container_width=True, config={"displayModeBar": False})

        last_rsi = df["RSI14"].iloc[-1]
        st.metric("RSI (14) actual", f"{last_rsi:.1f}" if pd.notna(last_rsi) else "—")

# =========================================================
# TAB: DXY & US02Y
# =========================================================
with tab_macro:
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown('<div class="cgb-label">Índice del Dólar (DXY) — velas diarias</div>', unsafe_allow_html=True)
            if df_dxy.empty:
                st.warning("No disponible en este momento.")
            else:
                fig = go.Figure(go.Candlestick(
                    x=df_dxy.index, open=df_dxy["Open"], high=df_dxy["High"], low=df_dxy["Low"], close=df_dxy["Close"],
                    increasing_line_color=BULL, decreasing_line_color=BEAR, name="DXY",
                ))
                fig.update_layout(height=380, xaxis_rangeslider_visible=False, **PLOTLY_LAYOUT)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with c2:
        with st.container(border=True):
            st.markdown('<div class="cgb-label">Rendimiento Bono USA 2 años (US02Y)</div>', unsafe_allow_html=True)
            if df_us02y.empty:
                st.warning("No disponible en este momento (fuente: FRED).")
            else:
                fig = go.Figure(go.Scatter(
                    x=df_us02y.index, y=df_us02y.iloc[:, 0], line=dict(color=PRIMARY_LIGHT, width=2),
                    fill="tozeroy", fillcolor="rgba(232,199,102,0.08)",
                ))
                fig.update_layout(height=380, **PLOTLY_LAYOUT)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("Correlación habitual: un dólar y unos yields fuertes suelen presionar al oro a la baja, y viceversa. No es una regla fija.")

# =========================================================
# TAB: COT
# =========================================================
with tab_cot:
    df_cot = get_cot_gold()
    if df_cot.empty:
        st.warning("No se pudo cargar el informe COT en este momento (fuente: CFTC public reporting). Prueba a recargar en unos segundos.")
    else:
        with st.container(border=True):
            render_cot_table(df_cot.iloc[-1])

        if "noncomm_positions_long_all" in df_cot.columns:
            with st.container(border=True):
                st.markdown('<div class="cgb-label">Evolución del posicionamiento (contrato estándar de Oro)</div>', unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_cot["report_date_as_yyyy_mm_dd"], y=df_cot["noncomm_positions_long_all"], name="Grandes esp. — Largos", line=dict(color=BULL)))
                fig.add_trace(go.Scatter(x=df_cot["report_date_as_yyyy_mm_dd"], y=df_cot["noncomm_positions_short_all"], name="Grandes esp. — Cortos", line=dict(color=BEAR)))
                if "comm_positions_long_all" in df_cot.columns:
                    fig.add_trace(go.Scatter(x=df_cot["report_date_as_yyyy_mm_dd"], y=df_cot["comm_positions_long_all"], name="Comerciales — Largos", line=dict(color=BLUE, dash="dot")))
                fig.update_layout(height=380, **PLOTLY_LAYOUT)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("El informe COT se publica semanalmente (viernes) con datos del martes anterior. Fuente: CFTC, contrato estándar de Oro (COMEX, 100 oz).")

# =========================================================
# TAB: MUROS DE OPCIONES
# =========================================================
with tab_opciones:
    with st.container(border=True):
        st.markdown('<div class="cgb-label">Muros de Open Interest — Opciones sobre ETFs de oro (proxy)</div>', unsafe_allow_html=True)
        calls, puts, exp, ticker_usado = get_options_walls()
        if calls.empty and puts.empty:
            st.warning("No se pudo cargar la cadena de opciones en este momento. Prueba a recargar en unos segundos.")
        else:
            st.caption(f"Fuente: opciones de {ticker_usado} · Vencimiento más próximo: {exp}")
            top_calls = calls.sort_values("openInterest", ascending=False).head(8)
            top_puts = puts.sort_values("openInterest", ascending=False).head(8)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=top_calls["strike"], y=top_calls["openInterest"], name="Calls (resistencias)", marker_color=BULL))
            fig.add_trace(go.Bar(x=top_puts["strike"], y=top_puts["openInterest"], name="Puts (soportes)", marker_color=BEAR))
            fig.update_layout(height=420, barmode="group", **PLOTLY_LAYOUT)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.caption(f"Strikes con mayor Open Interest en calls (posibles resistencias) y puts (posibles soportes) sobre {ticker_usado}, ETF que sigue de cerca el precio del oro.")

# =========================================================
# TAB: NOTICIAS
# =========================================================
with tab_noticias:
    st.markdown('<div class="cgb-label" style="margin-bottom:10px;">Noticias recientes</div>', unsafe_allow_html=True)
    noticias = get_news()
    if not noticias:
        st.warning("No se pudieron cargar noticias en este momento.")
    else:
        for n in noticias:
            st.markdown(f"""
            <div class="cgb-news-card">
                <a href="{n['link']}" target="_blank" class="cgb-news-title">{n['titulo']}</a>
                <div class="cgb-news-meta">{n['fecha']}</div>
            </div>
            """, unsafe_allow_html=True)

st.markdown('<div class="cgb-footer">CGB COMUNITY — Herramienta informativa y educativa. No constituye asesoramiento financiero ni una recomendación de inversión.</div>', unsafe_allow_html=True)
