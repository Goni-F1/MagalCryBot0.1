import os
import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta

TWELVE_DATA_KEY = os.environ.get("TWELVE_DATA_KEY")
SYMBOL = "EUR/USD"
INTERVAL = "3min"
OUTPUTSIZE = 80  # enough for all indicators on 3m candles
TRADE_DURATION_MINUTES = 3


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
        "open": "Open", "high": "High", "low": "Low",
        "close": "Close", "volume": "Volume"
    })
    for col in ["Open", "High", "Low", "Close"]:
        df[col] = df[col].astype(float)
    df = df.iloc[::-1].reset_index(drop=True)  # oldest first
    return df


def compute_indicators(df):
    """Compute RSI, MACD, EMA, SMA, Bollinger Bands tuned for 3m scalping."""
    close = df["Close"]

    # RSI (7) — faster for short-term
    df["RSI"] = ta.rsi(close, length=7)

    # MACD (5, 13, 4) — tighter settings for 3m
    macd = ta.macd(close, fast=5, slow=13, signal=4)
    df["MACD"] = macd["MACD_5_13_4"]
    df["MACD_signal"] = macd["MACDs_5_13_4"]
    df["MACD_hist"] = macd["MACDh_5_13_4"]

    # EMA 9 & EMA 21 (fast MAs for scalping)
    df["EMA9"] = ta.ema(close, length=9)
    df["EMA21"] = ta.ema(close, length=21)

    # Bollinger Bands (10, 2) — shorter window for 3m
    bb = ta.bbands(close, length=10, std=2)
    df["BB_upper"] = bb["BBU_10_2.0"]
    df["BB_lower"] = bb["BBL_10_2.0"]
    df["BB_mid"] = bb["BBM_10_2.0"]

    return df


def evaluate_signals(df):
    """Vote across indicators, return direction and score."""
    row = df.iloc[-1]
    prev = df.iloc[-2]
    votes = []

    # --- RSI (7) ---
    rsi = row["RSI"]
    if rsi < 40:
        votes.append("BUY")
    elif rsi > 60:
        votes.append("SELL")
    else:
        votes.append("NEUTRAL")

    # --- MACD histogram momentum ---
    # Rising histogram = building bullish momentum
    hist_now = row["MACD_hist"]
    hist_prev = prev["MACD_hist"]
    macd_bull = row["MACD"] > row["MACD_signal"]
    macd_bear = row["MACD"] < row["MACD_signal"]

    if macd_bull and hist_now > hist_prev:
        votes.append("BUY")
    elif macd_bear and hist_now < hist_prev:
        votes.append("SELL")
    else:
        votes.append("NEUTRAL")

    # --- EMA9 vs EMA21 ---
    price = row["Close"]
    ema9 = row["EMA9"]
    ema21 = row["EMA21"]
    if price > ema9 and ema9 > ema21:
        votes.append("BUY")
    elif price < ema9 and ema9 < ema21:
        votes.append("SELL")
    else:
        votes.append("NEUTRAL")

    # --- Bollinger Bands ---
    if price <= row["BB_lower"]:
        votes.append("BUY")
    elif price >= row["BB_upper"]:
        votes.append("SELL")
    else:
        # Price position relative to midline as a tiebreaker
        if price > row["BB_mid"]:
            votes.append("BUY")
        else:
            votes.append("SELL")

    buy_count = votes.count("BUY")
    sell_count = votes.count("SELL")

    if buy_count >= 3:
        direction = "BUY"
        score = buy_count
    elif sell_count >= 3:
        direction = "SELL"
        score = sell_count
    else:
        direction = "WAIT"
        score = 0

    return direction, score, price


def analyze_signal():
    """Fetch, compute, evaluate — return a clean 3-minute signal message."""
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
                f"🔒 Expiry: *{expiry_time} UTC* (3 min)\n"
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
                f"🔒 Expiry: *{expiry_time} UTC* (3 min)\n"
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
