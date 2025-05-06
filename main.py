import logging
import os
import json
import asyncio
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from quart import Quart
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from hypercorn.asyncio import serve
from hypercorn.config import Config

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Quart app
app = Quart(__name__)
application: Application = None

# Firebase setup
firebase_cred = os.getenv("FIREBASE_CREDENTIALS")
if not firebase_cred:
    raise ValueError("FIREBASE_CREDENTIALS not set")

try:
    cred_data = json.loads(firebase_cred)
    cred = credentials.Certificate(cred_data)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("Firebase initialized.")
except Exception as e:
    logger.error(f"Firebase error: {e}")
    raise

# Save user on /start
async def save_user(update: Update):
    user = update.effective_user
    user_ref = db.collection("users").document(str(user.id))
    user_ref.set({
        "telegram_id": str(user.id),
        "username": f"@{user.username}" if user.username else "unknown",
        "user_id": "Telegram api",
        "joined_at": datetime.utcnow(),
        "last_action": "start",
        "subscribed": True,
        "balance": 100,
        "binance_api_key": None,
        "binance_api_secret": None,
        "luno_api_key": None,
        "luno_api_secret": None,
        "trade_status": "inactive"
    }, merge=True)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save_user(update)
    context.user_data['step'] = 'awaiting_binance_key'
    await update.message.reply_text("Welcome! Please enter your *Binance API key*.", parse_mode="Markdown")

# Handle step-by-step API entry
async def handle_api_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    telegram_id = str(user.id)
    text = update.message.text
    step = context.user_data.get('step')

    doc_ref = db.collection("users").document(telegram_id)

    if step == 'awaiting_binance_key':
        context.user_data['binance_key'] = text
        context.user_data['step'] = 'awaiting_binance_secret'
        await update.message.reply_text("Now enter your *Binance API secret*.", parse_mode="Markdown")

    elif step == 'awaiting_binance_secret':
        context.user_data['binance_secret'] = text
        context.user_data['step'] = 'awaiting_luno_key'
        await update.message.reply_text("Now enter your *Luno API key*.", parse_mode="Markdown")

    elif step == 'awaiting_luno_key':
        context.user_data['luno_key'] = text
        context.user_data['step'] = 'awaiting_luno_secret'
        await update.message.reply_text("Now enter your *Luno API secret*.", parse_mode="Markdown")

    elif step == 'awaiting_luno_secret':
        context.user_data['luno_secret'] = text

        # Save to Firestore
        doc_ref.set({
            "binance_api_key": context.user_data['binance_key'],
            "binance_api_secret": context.user_data['binance_secret'],
            "luno_api_key": context.user_data['luno_key'],
            "luno_api_secret": context.user_data['luno_secret']
        }, merge=True)

        context.user_data.clear()
        await update.message.reply_text("✅ Your API keys have been saved successfully!")

    else:
        await update.message.reply_text("Please type /start to begin linking your API keys.")

# Main bot setup
async def main():
    global application
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN is not set")

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api_flow))

    webhook_url = f"https://crypto-bot-3-white-wind-424.fly.dev/webhook/{token}"
    await application.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")

    config = Config()
    config.bind = ["0.0.0.0:8080"]
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(main())
