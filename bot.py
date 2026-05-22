import os
import logging
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
from analyzer import analyze_signal
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

last_signal = {"direction": None}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *EUR/USD 3-Min Signal Bot*\n\n"
        "I send BUY ⬆️ or SELL ⬇️ signals every 5 minutes.\n"
        "Each signal includes an exact expiry time.\n\n"
        "Indicators used:\n"
        "• RSI (7)\n"
        "• MACD (5/13/4)\n"
        "• EMA 9 / EMA 21\n"
        "• Bollinger Bands (10)\n\n"
        "Signal fires only when 3+ indicators agree.\n\n"
        "Commands:\n"
        "/start — This message\n"
        "/signal — Get signal right now\n"
        "/status — Bot health",
        parse_mode="Markdown"
    )


async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Analyzing EUR/USD (3m)...")
    msg, _ = analyze_signal()
    await update.message.reply_text(msg, parse_mode="Markdown")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"✅ Bot running\n"
        f"📊 Pair: EUR/USD\n"
        f"⏱ Interval: every 5 minutes\n"
        f"📡 Last signal: {last_signal['direction'] or 'None yet'}"
    )


async def scheduled_check(app: Application):
    msg, direction = analyze_signal()

    if direction in ("BUY", "SELL"):
        # Always send BUY/SELL — each candle is a fresh 3-min trade opportunity
        last_signal["direction"] = direction
        await app.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
        logger.info(f"Signal sent: {direction}")
    elif direction is None:
        logger.warning("Signal fetch failed.")
    else:
        # WAIT — only log, don't spam the user
        last_signal["direction"] = "WAIT"
        logger.info("Signal: WAIT — not sent.")


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(CommandHandler("status", status))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scheduled_check,
        "interval",
        minutes=5,
        args=[app]
    )
    scheduler.start()

    logger.info("Bot started — checking EUR/USD every 5 minutes.")
    app.run_polling()


if __name__ == "__main__":
    main()
