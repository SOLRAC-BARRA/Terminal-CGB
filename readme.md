[README-2.md](https://github.com/user-attachments/files/31421764/README-2.md)
# CGB Terminal — XAU/USD Market Intelligence

Professional Streamlit terminal for quantitative analysis of gold (XAU/USD).

## What changed

This version keeps the original analytical engines while rebuilding the interface as a professional research terminal:

- Persistent left sidebar navigation.
- No decorative emojis in the interface.
- Four professional visual themes.
- Configurable number of support and resistance levels.
- Cleaner institutional-style cards, typography and spacing.
- Executive quantitative bias score.
- Gold technical analysis: candles, EMA 20/50/200, Bollinger Bands, RSI and ATR.
- Macro dashboard: DXY, US 2Y and rolling Gold/DXY correlation.
- CFTC COT positioning.
- Options open-interest structure using GLD/IAU.
- Position sizing calculator.
- News flow screen with bullish/bearish/neutral classification.
- Data-integrity indicators.
- Responsive layout for desktop and smaller screens.

## Files

```text
CGB_Terminal_Professional/
├── app.py
├── requirements.txt
├── README.md
└── .streamlit/
    └── config.toml
```

Keep your existing `logo.jpg` in the same folder as `app.py` if you want the CGB logo to appear in the interface.

## Run locally

Install Python 3.10+.

```bash
pip install -r requirements.txt
streamlit run app.py
```

## GitHub / Streamlit Cloud

1. Create or open your GitHub repository.
2. Replace the old `app.py` with this `app.py`.
3. Replace `requirements.txt`.
4. Upload the `.streamlit/config.toml` folder and this README.
5. Keep `logo.jpg` in the repository root.
6. In Streamlit Cloud, select the repository and set the main file to `app.py`.

## Important data note

The original application uses Yahoo Finance, FRED/CFTC and RSS feeds. Availability and update frequency depend on those external providers. The interface therefore avoids claiming that every source is truly tick-by-tick real-time.

## Risk calculator

The position-size calculation depends on the contract specification. The application exposes the USD P/L per $1.00 move per lot so you can set it to the specification of your broker/instrument.
