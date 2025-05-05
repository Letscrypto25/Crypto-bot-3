import logging
import os
from quart import Quart, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Quart app for webhook handling
flask_app = Quart(__name__)

# Prevent KeyError in newer Flask/Quart versions
flask_app.config["PROVIDE_AUTOMATIC_OPTIONS"] = flask_app.config.get("PROVIDE_AUTOMATIC_OPTIONS", True)

# Global Telegram app instance
application: Application = None

@flask_app.route("/")
async def health_check():
    return "OK", 200

@flask_app.route(f"/webhook/<token>", methods=["POST"])
async def telegram_webhook(token):
    if token != os.getenv("BOT_TOKEN"):
        logger.error(f"Unauthorized access: Token mismatch. Expected {os.getenv('BOT_TOKEN')}, got {token}")
        return "Unauthorized", 403

    logger.info(f"Received webhook for token: {token}")
    update = Update.de_json(await request.json, application.bot)
    await application.process_update(update)
    return "OK", 200

# Telegram command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello, I am your crypto trading bot!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("How can I assist you with your crypto trades?")

# Setup Telegram bot and webhook on startup
@flask_app.before_serving
async def setup_bot():
    global application
    TOKEN = os.getenv("BOT_TOKEN")
    webhook_url = f"https://crypto-bot-3-white-wind-424.fly.dev/webhook/{TOKEN}"

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    await application.bot.set_webhook(webhook_url)
    logger.info("Webhook set and bot ready!")
