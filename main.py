import logging
import os
from quart import Quart, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

flask_app = Quart(__name__)
flask_app.config["PROVIDE_AUTOMATIC_OPTIONS"] = flask_app.config.get("PROVIDE_AUTOMATIC_OPTIONS", True)

application: Application = None

@flask_app.route("/")
async def health_check():
    return "OK", 200

@flask_app.route(f"/webhook/<token>", methods=["POST"])
async def telegram_webhook(token):
    if token != os.getenv("BOT_TOKEN"):
        logger.error("Invalid token in webhook URL.")
        return "Unauthorized", 403

    update = Update.de_json(await request.json, application.bot)
    await application.process_update(update)
    return "OK", 200

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello, I am your crypto trading bot!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("How can I assist you with your crypto trades?")

@flask_app.before_serving
async def setup_bot():
    global application
    try:
        TOKEN = os.getenv("BOT_TOKEN")
        if not TOKEN:
            raise ValueError("BOT_TOKEN not set in environment")

        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))

        webhook_url = f"https://crypto-bot-3-white-wind-424.fly.dev/webhook/{TOKEN}"
        await application.bot.set_webhook(webhook_url)

        logger.info("Webhook set and bot ready!")
    except Exception as e:
        logger.exception("Error during bot setup")

if __name__ == "__main__":
    import asyncio
    import hypercorn.asyncio
    from hypercorn.config import Config

    config = Config()
    config.bind = ["0.0.0.0:8080"]

    asyncio.run(hypercorn.asyncio.serve(flask_app, config))
