import logging
import os
import json
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import firebase_admin
from firebase_admin import credentials

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firebase using secret from environment variable
firebase_credentials_json = os.getenv("FIREBASE_CREDENTIALS")
cred_dict = json.loads(firebase_credentials_json)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)

# Flask app for health checks
flask_app = Flask(__name__)

@flask_app.route("/")
def health_check():
    return "OK", 200

# Telegram command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello, I am your crypto trading bot!")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("How can I assist you with your crypto trades?")

async def get_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Your current balance is: R1000")

async def check_trends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Current crypto trends: Bitcoin is trending upward.")

# Main bot setup
async def setup_bot():
    global application
    TOKEN = os.getenv("BOT_TOKEN")
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("get_balance", get_balance))
    application.add_handler(CommandHandler("check_trends", check_trends))

    # Set webhook (Telegram will send updates to this)
    webhook_url = f"https://crypto-bot-3-white-wind-424.fly.dev/webhook/{TOKEN}"
    await application.bot.set_webhook(webhook_url)

# Flask route to handle incoming webhook requests
@flask_app.route(f"/webhook/<token>", methods=["POST"])
def telegram_webhook(token):
    # Check if the token in the URL matches the bot's token
    if token != os.getenv("BOT_TOKEN"):
        return "Unauthorized", 403

    # Process the update from Telegram
    request_data = request.get_data().decode("utf-8")
    update = Update.de_json(json.loads(request_data), application.bot)
    asyncio.create_task(application.process_update(update))
    return "OK", 200

# Run the bot
if __name__ == "__main__":
    asyncio.run(setup_bot())
    flask_app.run(host="0.0.0.0", port=8080)
