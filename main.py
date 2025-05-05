import logging
import os
import asyncio

from quart import Quart, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from hypercorn.asyncio import serve
from hypercorn.config import Config

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Quart app
app = Quart(__name__)
application: Application = None  # Telegram app

@app.route("/")
async def health_check():
    return "OK", 200

@app.route("/webhook/<token>", methods=["POST"])
async def telegram_webhook(token):
    if token != os.getenv("BOT_TOKEN"):
        logger.error("Invalid token in webhook URL.")
        return "Unauthorized", 403

    try:
        update = Update.de_json(await request.get_json(), application.bot)
        await application.process_update(update)
    except Exception as e:
        logger.exception("Failed to process update")
        return "Internal Server Error", 500

    return "OK", 200

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello, I am your crypto trading bot!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("How can I assist you with your crypto trades?")

@app.before_serving
async def setup_bot():
    global application
    try:
        token = os.getenv("BOT_TOKEN")
        if not token:
            raise ValueError("BOT_TOKEN is not set")

        application = Application.builder().token(token).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))

        webhook_url = f"https://crypto-bot-3-white-wind-424.fly.dev/webhook/{token}"
        await application.bot.set_webhook(webhook_url)

        logger.info(f"Bot is live with webhook: {webhook_url}")
    except Exception as e:
        logger.exception("Error during bot setup")

if __name__ == "__main__":
    config = Config()
    config.bind = ["0.0.0.0:8080"]
    asyncio.run(serve(app, config))
