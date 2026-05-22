import os
import requests
import pandas as pd
import numpy as np
import ta
from datetime import datetime, timedelta

TWELVE_DATA_KEY = os.environ.get("TWELVE_DATA_KEY")
SYMBOL = "EUR/USD"
INTERVAL = "5min"
OUTPUTSIZE = 80
TRADE_DURATION_MINUTES = 5


def fetch_ohlcv():
    """Fetch EUR/USD 3-minute candles from Twelve Data."""
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "outputsize": OUTPUTSIZE,
        "apikey": TWELVE_DATA_KEY,
        "format": "JSON"
    }
    resp = requests.get(url, params=params, timeout=15)
    data = resp.json()

    if "values" not in data:
        raise ValueError(f"API error: {data.get('message', 'Unknown error')}")

    df = pd.DataFrame(data["values"])
    df = df.rename(columns={
        "open": "Open", "high": "High",
        "low": "Low", "close": "Close"
    })
    for col in ["Open", "High", "Low", "Close"]:
        df[col] = df[col].astype(float)
    df = df.iloc[::-1].reset_index(drop=True)  # oldest first
    return df


def compute_indicators(df):
    """Compute RSI, MACD, EMA, Bollinger Bands using 'ta' library."""
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    # RSI (7) — fast for 3m scalping
    df["RSI"] = ta.momentum.RSIIndicator(close, window=7).rsi()

    # MACD (5, 13, 4)
    macd_ind = ta.trend.MACD(close, window_fast=5, window_slow=13, window_sign=4)
    df["MACD"] = macd_ind.macd()
    df["MACD_signal"] = macd_ind.macd_signal()
    df["MACD_hist"] = macd_ind.macd_diff()

    # EMA 9 and EMA 21
    df["EMA9"] = ta.trend.EMAIndicator(close, window=9).ema_indicator()
    df["EMA21"] = ta.trend.EMAIndicator(close, window=21).ema_indicator()

    # Bollinger Bands (10, 2)
    bb = ta.volatility.BollingerBands(close, window=10, window_dev=2)
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_lower"] = bb.bollinger_lband()
    df["BB_mid"] = bb.bollinger_mavg()

    return df


def evaluate_signals(df):
    """Vote across 4 indicators for BUY / SELL / WAIT."""
    row = df.iloc[-1]
    prev = df.iloc[-2]
    votes = []

    # --- RSI ---
    rsi = row["RSI"]
    if rsi < 40:
        votes.append("BUY")
    elif rsi > 60:
        votes.append("SELL")
    else:
        votes.append("NEUTRAL")

    # --- MACD histogram momentum ---
    if row["MACD"] > row["MACD_signal"] and row["MACD_hist"] > prev["MACD_hist"]:
        votes.append("BUY")
    elif row["MACD"] < row["MACD_signal"] and row["MACD_hist"] < prev["MACD_hist"]:
        votes.append("SELL")
    else:
        votes.append("NEUTRAL")

    # --- EMA9 vs EMA21 ---
    price = row["Close"]
    if price > row["EMA9"] and row["EMA9"] > row["EMA21"]:
        votes.append("BUY")
    elif price < row["EMA9"] and row["EMA9"] < row["EMA21"]:
        votes.append("SELL")
    else:
        votes.append("NEUTRAL")

    # --- Bollinger Bands ---
    if price <= row["BB_lower"]:
        votes.append("BUY")
    elif price >= row["BB_upper"]:
        votes.append("SELL")
    else:
        votes.append("BUY" if price > row["BB_mid"] else "SELL")

    buy_count = votes.count("BUY")
    sell_count = votes.count("SELL")

    if buy_count >= 3:
        return "BUY", buy_count, price
    elif sell_count >= 3:
        return "SELL", sell_count, price
    else:
        return "WAIT", 0, price


def analyze_signal():
    """Main entry point — returns (message, direction)."""
    try:
        df = fetch_ohlcv()
        df = compute_indicators(df)
        direction, score, price = evaluate_signals(df)

        now_utc = datetime.utcnow()
        expiry_utc = now_utc + timedelta(minutes=TRADE_DURATION_MINUTES)
        entry_time = now_utc.strftime("%H:%M")
        expiry_time = expiry_utc.strftime("%H:%M")

        if direction == "BUY":
            msg = (
                f"⬆️ *BUY — EUR/USD*\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"💱 Entry: `{price:.5f}`\n"
                f"⏱ Open at: *{entry_time} UTC*\n"
                f"🔒 Expiry: *{expiry_time} UTC* (5 min)\n"
                f"📶 Strength: {score}/4 indicators\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"✅ Open a *BUY* trade on ExpertOption now"
            )
        elif direction == "SELL":
            msg = (
                f"⬇️ *SELL — EUR/USD*\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"💱 Entry: `{price:.5f}`\n"
                f"⏱ Open at: *{entry_time} UTC*\n"
                f"🔒 Expiry: *{expiry_time} UTC* (5 min)\n"
                f"📶 Strength: {score}/4 indicators\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"✅ Open a *SELL* trade on ExpertOption now"
            )
        else:
            msg = (
                f"⏳ *WAIT — EUR/USD*\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"💱 Price: `{price:.5f}`\n"
                f"⏱ Checked: *{entry_time} UTC*\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📉 Signal too weak — skip this candle"
            )

        return msg, direction

    except Exception as e:
        return f"⚠️ Error: {str(e)}", None
