import logging
import os
import asyncio
import json
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore

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
application: Application = None  # Telegram application
initialized = False

# Initialize Firebase
firebase_cred = os.getenv("FIREBASE_CREDENTIALS")
if not firebase_cred:
    logger.error("FIREBASE_CREDENTIALS not set")
    raise ValueError("FIREBASE_CREDENTIALS not set")

# Parse the credentials from the JSON string
try:
    cred_data = json.loads(firebase_cred)  # Convert JSON string to dictionary
    cred = credentials.Certificate(cred_data)  # Pass dictionary to Firebase credentials
    firebase_admin.initialize_app(cred)  # Initialize Firebase app
    db = firestore.client()  # Create Firestore client
    logger.info("Firebase initialized successfully.")
except json.JSONDecodeError:
    logger.error("Invalid JSON format for Firebase credentials.")
    raise
except Exception as e:
    logger.error(f"Error initializing Firebase: {e}")
    raise

# Health check route
@app.route("/")
async def health_check():
    return "OK", 200

# Webhook route for handling Telegram updates
@app.route("/webhook/<token>", methods=["POST"])
async def telegram_webhook(token):
    global application, initialized
    if token != os.getenv("BOT_TOKEN"):
        logger.error("Invalid token in webhook URL.")
        return "Unauthorized", 403

    try:
        if not initialized:
            await application.initialize()
            initialized = True

        update = Update.de_json(await request.get_json(), application.bot)
        await application.process_update(update)
    except Exception:
        logger.exception("Failed to process update")
        return "Internal Server Error", 500

    return "OK", 200

# Function to save user data to Firestore
async def save_user(update: Update):
    user = update.effective_user
    user_ref = db.collection("users").document(str(user.id))

    user_data = {
        "telegram_id": user.id,
        "username": f"@{user.username}" if user.username else "unknown",
        "user_id": "Telegram api",  # Optional or can be updated later
        "joined_at": datetime.utcnow(),
        "last_action": "start",
        "balance": 100,
        "subscribed": True,
    }

    user_ref.set(user_data, merge=True)

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save_user(update)
    await update.message.reply_text("Hello, I am your crypto trading bot!")

# /help command handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("How can I assist you with your crypto trades?")

# Main async entry point
async def main():
    global application
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN not set")
        raise ValueError("BOT_TOKEN is not set")

    # Initialize Telegram bot application
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Set the Telegram webhook URL
    webhook_url = f"https://crypto-bot-3-white-wind-424.fly.dev/webhook/{token}"
    await application.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")

    # Start Quart web server
    config = Config()
    config.bind = ["0.0.0.0:8080"]
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(main())
