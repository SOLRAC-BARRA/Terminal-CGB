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

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import requests
import feedparser
from datetime import datetime, timedelta

# =========================================================
# CONFIGURACIÓN GENERAL DE LA PÁGINA
# =========================================================
st.set_page_config(
    page_title="CGB COMUNITY | Terminal XAU/USD",
    page_icon="🥇",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estética general (tema oscuro tipo "trading desk")
st.markdown("""
<style>
    .stApp { background-color: #0b0e14; }
    section[data-testid="stSidebar"] { background-color: #10141d; }
    h1, h2, h3 { color: #f2f2f2; }
    .cgb-card {
        background-color: #131722;
        border: 1px solid #232838;
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 14px;
    }
    .cgb-metric-label { color: #8a93a6; font-size: 0.8rem; text-transform: uppercase; letter-spacing: .05em; }
    .cgb-metric-value { font-size: 1.6rem; font-weight: 700; color: #f2f2f2; }
    .cgb-bull { color: #29d391; }
    .cgb-bear { color: #ff5c72; }
    .cgb-neutral { color: #f2c94c; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# FUNCIONES DE DATOS (con caché para no pedir de más a las APIs)
# =========================================================

@st.cache_data(ttl=300)
def get_price_data(ticker: str, period: str = "9mo", interval: str = "1d") -> pd.DataFrame:
    """Descarga histórico de precios con yfinance (gratis, sin API key)."""
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df.dropna()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def get_us02y() -> pd.DataFrame:
    """Rendimiento del bono USA a 2 años, vía FRED (gratis, sin API key)."""
    try:
        import pandas_datareader.data as web
        end = datetime.today()
        start = end - timedelta(days=400)
        df = web.DataReader("DGS2", "fred", start, end)
        return df.dropna()
    except Exception:
        return pd.DataFrame()


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


def pivot_points(df: pd.DataFrame) -> dict:
    """Pivotes clásicos calculados con la última vela diaria cerrada."""
    last = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
    h, l, c = float(last["High"]), float(last["Low"]), float(last["Close"])
    pp = (h + l + c) / 3
    r1, s1 = 2 * pp - l, 2 * pp - h
    r2, s2 = pp + (h - l), pp - (h - l)
    r3, s3 = h + 2 * (pp - l), l - 2 * (h - pp)
    return {"R3": r3, "R2": r2, "R1": r1, "PP": pp, "S1": s1, "S2": s2, "S3": s3}


@st.cache_data(ttl=1800)
def get_cot_gold() -> pd.DataFrame:
    """Informe COT (CFTC) 'Disaggregated Futures Only' para el oro. Gratis, sin API key."""
    url = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
    params = {
        "$where": "market_and_exchange_names like 'GOLD%25COMMODITY EXCHANGE%25'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": 26,
    }
    try:
        r = requests.get(url, params=params, timeout=12)
        r.raise_for_status()
        df = pd.DataFrame(r.json())
        if df.empty:
            return df
        num_cols = [c for c in df.columns if "positions" in c or "open_interest" in c]
        for c in num_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["report_date_as_yyyy_mm_dd"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"])
        return df.sort_values("report_date_as_yyyy_mm_dd")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=1800)
def get_options_walls(ticker: str = "GLD"):
    """
    Muros de mercado de opciones vía Open Interest del ETF GLD (proxy líquido del oro,
    ya que los futuros GC no publican cadena de opciones abierta en yfinance).
    """
    try:
        tk = yf.Ticker(ticker)
        exps = tk.options
        if not exps:
            return pd.DataFrame(), pd.DataFrame(), None
        exp = exps[0]
        chain = tk.option_chain(exp)
        calls = chain.calls[["strike", "openInterest", "volume"]].groupby("strike").sum().reset_index()
        puts = chain.puts[["strike", "openInterest", "volume"]].groupby("strike").sum().reset_index()
        return calls, puts, exp
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), None


@st.cache_data(ttl=900)
def get_news():
    """Titulares recientes relacionados con oro/macro vía RSS (gratis, sin API key)."""
    feeds = [
        "https://www.investing.com/rss/commodities_Gold.rss",
        "https://www.investing.com/rss/news_285.rss",
        "https://www.forexlive.com/feed/news",
    ]
    items = []
    for f in feeds:
        try:
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
# CÁLCULO DEL SESGO DEL DÍA (score propio 0-100)
# =========================================================

def calcular_sesgo(df_gold, df_dxy, df_us02y):
    """
    Combina varias señales normalizadas 0-100 en un score único.
    Esto es una heurística propia, NO un modelo predictivo validado.
    """
    señales = {}

    if not df_gold.empty and len(df_gold) > 20:
        close = df_gold["Close"]
        r = rsi(close).iloc[-1]
        señales["RSI (14)"] = float(np.clip(r, 0, 100))

        mom20 = (close.iloc[-1] / close.iloc[-20] - 1) * 100
        señales["Momentum 20d"] = float(np.clip(50 + mom20 * 4, 0, 100))

        ema20, ema50 = ema(close, 20).iloc[-1], ema(close, 50).iloc[-1]
        tendencia = 70 if close.iloc[-1] > ema20 > ema50 else (30 if close.iloc[-1] < ema20 < ema50 else 50)
        señales["Tendencia (EMA)"] = tendencia

        atr_pct = (atr(df_gold).iloc[-1] / close.iloc[-1]) * 100
        estabilidad = float(np.clip(100 - atr_pct * 25, 0, 100))
        señales["Estabilidad (ATR)"] = estabilidad

    # DXY inverso: dólar fuerte suele presionar el oro a la baja
    if not df_dxy.empty and len(df_dxy) > 6:
        dxy_close = df_dxy["Close"]
        dxy_mom = (dxy_close.iloc[-1] / dxy_close.iloc[-6] - 1) * 100
        señales["DXY (inverso)"] = float(np.clip(50 - dxy_mom * 8, 0, 100))

    # US02Y inverso: yields al alza suelen presionar el oro a la baja
    if not df_us02y.empty and len(df_us02y) > 6:
        y = df_us02y.iloc[:, 0]
        y_mom = y.iloc[-1] - y.iloc[-6]
        señales["US02Y (inverso)"] = float(np.clip(50 - y_mom * 20, 0, 100))

    if not señales:
        return 50, "Sin datos suficientes", señales

    score = float(np.mean(list(señales.values())))
    if score >= 65:
        etiqueta = "Sesgo Alcista"
    elif score <= 35:
        etiqueta = "Sesgo Bajista"
    else:
        etiqueta = "Sesgo Neutral"
    return score, etiqueta, señales


# =========================================================
# CABECERA
# =========================================================
st.markdown("## 🥇 CGB COMUNITY — Terminal XAU/USD")
st.caption("Análisis diario del oro combinando GC, DXY, US02Y, ATR, EMA, volumen, COT, muros de opciones y noticias. Uso educativo — no es asesoramiento financiero.")

with st.spinner("Cargando datos de mercado..."):
    df_gold = get_price_data("GC=F")
    df_dxy = get_price_data("DX-Y.NYB")
    if df_dxy.empty:
        df_dxy = get_price_data("DX=F")
    df_us02y = get_us02y()

tab_resumen, tab_oro, tab_macro, tab_cot, tab_opciones, tab_noticias = st.tabs(
    ["📊 Resumen del día", "🥇 Oro (XAU/USD)", "💵 DXY & US02Y", "🏦 COT", "🧱 Muros de opciones", "📰 Noticias"]
)

# =========================================================
# TAB: RESUMEN DEL DÍA
# =========================================================
with tab_resumen:
    score, etiqueta, señales = calcular_sesgo(df_gold, df_dxy, df_us02y)

    color_clase = "cgb-bull" if score >= 65 else ("cgb-bear" if score <= 35 else "cgb-neutral")
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown(f"""
        <div class="cgb-card" style="text-align:center;">
            <div class="cgb-metric-label">Score CGB del día</div>
            <div class="cgb-metric-value {color_clase}" style="font-size:3rem;">{score:.0f}</div>
            <div class="{color_clase}" style="font-size:1.2rem; font-weight:600;">{etiqueta}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        if señales:
            fig = go.Figure(go.Bar(
                x=list(señales.values()),
                y=list(señales.keys()),
                orientation="h",
                marker_color=["#29d391" if v >= 55 else ("#ff5c72" if v <= 45 else "#f2c94c") for v in señales.values()],
            ))
            fig.update_layout(
                xaxis_range=[0, 100], height=280, margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="#131722", plot_bgcolor="#131722", font_color="#f2f2f2",
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    if not df_gold.empty:
        precio = df_gold["Close"].iloc[-1]
        var = (df_gold["Close"].iloc[-1] / df_gold["Close"].iloc[-2] - 1) * 100
        c1.metric("Oro (GC=F)", f"${precio:,.2f}", f"{var:+.2f}%")
    if not df_dxy.empty:
        dxy_val = df_dxy["Close"].iloc[-1]
        dxy_var = (df_dxy["Close"].iloc[-1] / df_dxy["Close"].iloc[-2] - 1) * 100
        c2.metric("DXY", f"{dxy_val:,.2f}", f"{dxy_var:+.2f}%")
    if not df_us02y.empty:
        y_val = df_us02y.iloc[-1, 0]
        y_prev = df_us02y.iloc[-2, 0]
        c3.metric("US 2Y Yield", f"{y_val:.2f}%", f"{(y_val - y_prev):+.2f} pts")

    st.markdown("---")
    if not df_gold.empty:
        piv = pivot_points(df_gold)
        st.markdown("#### Puntos pivote (diario)")
        cols = st.columns(7)
        for i, k in enumerate(["R3", "R2", "R1", "PP", "S1", "S2", "S3"]):
            cols[i].metric(k, f"{piv[k]:,.1f}")

# =========================================================
# TAB: ORO — precio, EMA, ATR, volumen
# =========================================================
with tab_oro:
    if df_gold.empty:
        st.warning("No se pudieron cargar los datos del oro en este momento.")
    else:
        df = df_gold.copy()
        df["EMA20"] = ema(df["Close"], 20)
        df["EMA50"] = ema(df["Close"], 50)
        df["EMA200"] = ema(df["Close"], 200)
        df["ATR14"] = atr(df, 14)
        df["RSI14"] = rsi(df["Close"], 14)

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="XAU/USD"
        ))
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA20"], line=dict(color="#29d391", width=1), name="EMA 20"))
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], line=dict(color="#4da6ff", width=1), name="EMA 50"))
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA200"], line=dict(color="#f2c94c", width=1), name="EMA 200"))
        fig.update_layout(
            height=500, xaxis_rangeslider_visible=False, paper_bgcolor="#131722",
            plot_bgcolor="#131722", font_color="#f2f2f2", margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            fig_vol = go.Figure(go.Bar(x=df.index, y=df["Volume"], marker_color="#4da6ff"))
            fig_vol.update_layout(title="Volumen", height=250, paper_bgcolor="#131722", plot_bgcolor="#131722", font_color="#f2f2f2", margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_vol, use_container_width=True)
        with c2:
            fig_atr = go.Figure(go.Scatter(x=df.index, y=df["ATR14"], line=dict(color="#ff5c72")))
            fig_atr.update_layout(title="ATR (14) — Volatilidad", height=250, paper_bgcolor="#131722", plot_bgcolor="#131722", font_color="#f2f2f2", margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_atr, use_container_width=True)

        st.metric("RSI (14) actual", f"{df['RSI14'].iloc[-1]:.1f}")

# =========================================================
# TAB: MACRO — DXY & US02Y
# =========================================================
with tab_macro:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Índice del Dólar (DXY)")
        if df_dxy.empty:
            st.warning("No disponible en este momento.")
        else:
            fig = go.Figure(go.Scatter(x=df_dxy.index, y=df_dxy["Close"], line=dict(color="#4da6ff")))
            fig.update_layout(height=380, paper_bgcolor="#131722", plot_bgcolor="#131722", font_color="#f2f2f2", margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("#### Rendimiento Bono USA 2 años (US02Y)")
        if df_us02y.empty:
            st.warning("No disponible en este momento (fuente: FRED).")
        else:
            fig = go.Figure(go.Scatter(x=df_us02y.index, y=df_us02y.iloc[:, 0], line=dict(color="#f2c94c")))
            fig.update_layout(height=380, paper_bgcolor="#131722", plot_bgcolor="#131722", font_color="#f2f2f2", margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
    st.caption("Correlación habitual: Dólar y yields fuertes suelen presionar al oro a la baja, y viceversa (no es una regla fija).")

# =========================================================
# TAB: COT (CFTC)
# =========================================================
with tab_cot:
    st.markdown("#### Posicionamiento COT — Oro (Disaggregated Futures Only, CFTC)")
    df_cot = get_cot_gold()
    if df_cot.empty:
        st.warning("No se pudo cargar el informe COT en este momento (fuente: CFTC públic reporting).")
    else:
        posibles = [c for c in df_cot.columns if "noncomm_positions_long" in c or "noncomm_positions_short" in c]
        if len(posibles) >= 2:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_cot["report_date_as_yyyy_mm_dd"], y=df_cot[posibles[0]], name="Largos no comerciales", line=dict(color="#29d391")))
            fig.add_trace(go.Scatter(x=df_cot["report_date_as_yyyy_mm_dd"], y=df_cot[posibles[1]], name="Cortos no comerciales", line=dict(color="#ff5c72")))
            fig.update_layout(height=400, paper_bgcolor="#131722", plot_bgcolor="#131722", font_color="#f2f2f2", margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_cot.tail(10), use_container_width=True)
    st.caption("El informe COT se publica semanalmente (viernes) con datos del martes anterior.")

# =========================================================
# TAB: MUROS DE OPCIONES
# =========================================================
with tab_opciones:
    st.markdown("#### Muros de Open Interest — Opciones sobre GLD (proxy líquido del oro)")
    calls, puts, exp = get_options_walls("GLD")
    if calls.empty:
        st.warning("No se pudo cargar la cadena de opciones en este momento.")
    else:
        st.caption(f"Vencimiento más próximo: {exp}")
        top_calls = calls.sort_values("openInterest", ascending=False).head(8)
        top_puts = puts.sort_values("openInterest", ascending=False).head(8)

        fig = go.Figure()
        fig.add_trace(go.Bar(x=top_calls["strike"], y=top_calls["openInterest"], name="Calls (resistencias)", marker_color="#29d391"))
        fig.add_trace(go.Bar(x=top_puts["strike"], y=top_puts["openInterest"], name="Puts (soportes)", marker_color="#ff5c72"))
        fig.update_layout(height=420, barmode="group", paper_bgcolor="#131722", plot_bgcolor="#131722", font_color="#f2f2f2", margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Strikes con mayor Open Interest en calls (posibles resistencias) y puts (posibles soportes). GLD cotiza ≈ 1/10 del precio del oro.")

# =========================================================
# TAB: NOTICIAS
# =========================================================
with tab_noticias:
    st.markdown("#### Noticias recientes")
    noticias = get_news()
    if not noticias:
        st.warning("No se pudieron cargar noticias en este momento.")
    else:
        for n in noticias:
            st.markdown(f"""
            <div class="cgb-card">
                <a href="{n['link']}" target="_blank" style="color:#f2f2f2; text-decoration:none; font-weight:600;">{n['titulo']}</a>
                <div class="cgb-metric-label" style="margin-top:4px;">{n['fecha']}</div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")
st.caption("CGB COMUNITY — Herramienta informativa y educativa. No constituye asesoramiento financiero ni una recomendación de inversión.")
