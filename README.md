# EUR/USD Signal Bot — Setup Guide

A Telegram bot that analyzes EUR/USD every 15 minutes and sends BUY/SELL signals
based on RSI, MACD, EMA/SMA, and Bollinger Bands.

---

## Step 1: Get Your API Keys

### Telegram Bot Token
1. Open Telegram, search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the token (looks like `123456789:ABCdef...`)

### Your Telegram Chat ID
1. Search for **@userinfobot** on Telegram
2. Send `/start` — it will reply with your Chat ID (a number like `987654321`)

### Twelve Data API Key (Free)
1. Go to https://twelvedata.com
2. Sign up for a free account
3. Go to Dashboard → API Keys → copy your key
4. Free tier: 800 requests/day, 8 per minute — more than enough

---

## Step 2: Deploy to Railway

### A) Push to GitHub first
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/eurusd-signal-bot.git
git push -u origin main
```

### B) Deploy on Railway
1. Go to https://railway.app and sign in with GitHub
2. Click **New Project → Deploy from GitHub repo**
3. Select your repo
4. Click **Variables** and add these:

| Variable | Value |
|---|---|
| `TELEGRAM_TOKEN` | Your BotFather token |
| `CHAT_ID` | Your Telegram chat ID |
| `TWELVE_DATA_KEY` | Your Twelve Data API key |
| `CHECK_INTERVAL_MINUTES` | `15` |

5. Railway auto-detects the Procfile and starts the `worker`
6. Done! The bot is live.

---

## Step 3: Test It

In Telegram, send your bot:
- `/start` — welcome message
- `/signal` — get a signal right now
- `/status` — see bot health

---

## Signal Logic

| Indicator | BUY condition | SELL condition |
|---|---|---|
| RSI (14) | RSI < 40 | RSI > 60 |
| MACD | MACD line above signal | MACD line below signal |
| EMA20/SMA50 | Price > EMA20 > SMA50 | Price < EMA20 < SMA50 |
| Bollinger Bands | Price at/below lower band | Price at/above upper band |

**Signal is sent only when 3 or 4 indicators agree.**
Weak/mixed signals show "WAIT" — no noise.

---

## File Structure

```
bot/
├── bot.py           # Telegram bot + scheduler
├── analyzer.py      # Indicator logic + signal scoring
├── requirements.txt # Python dependencies
├── Procfile         # Railway process definition
└── .env.example     # Environment variable template
```

---

## Important Note

This bot provides **analysis signals only**. You manually execute trades on ExpertOption.
Past indicator performance does not guarantee future results. Trade responsibly.
