import logging
import os
import json
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
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

# Function to save user data to Firestore
async def save_user(update: Update):
    user = update.effective_user
    user_ref = db.collection("users").document(str(user.id))

    user_data = {
        "telegram_id": user.id,
        "username": f"@{user.username}" if user.username else "unknown",
        "user_id": "Telegram api",  # Can be updated later
        "joined_at": datetime.utcnow(),
        "last_action": "start",  # Default to "start", can update later
        "subscribed": True,  # Default to subscribed (can be updated)
        "balance": 100,  # Default balance (update based on actual trades)
        "binance_api": None,  # Placeholder for Binance API key
        "luno_api": None,  # Placeholder for Luno API key
        "trade_status": "inactive"  # Default status
    }

    # Save data to Firestore
    user_ref.set(user_data, merge=True)

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save_user(update)
    await update.message.reply_text("Hello, I am your crypto trading bot! Please send me your API keys to proceed.")

# Function to handle API keys input (Binance and Luno)
async def handle_api_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_ref = db.collection("users").document(str(user.id))
    user_data = context.user_data

    # Check the state and process API keys
    if user_data.get('state') == 'waiting_binance_api':
        binance_api = update.message.text
        context.user_data['binance_api'] = binance_api
        user_data['binance_api'] = binance_api
        await update.message.reply_text("Now, please send me your Luno API key.")
        context.user_data['state'] = 'waiting_luno_api'

    elif user_data.get('state') == 'waiting_luno_api':
        luno_api = update.message.text
        context.user_data['luno_api'] = luno_api
        user_data['luno_api'] = luno_api
        
        # Save to Firestore
        user_ref.set(user_data, merge=True)
        await update.message.reply_text("Your API keys have been saved successfully!")

        # Reset state after saving
        context.user_data['state'] = None

# Telegram command handlers
async def main():
    global application
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN not set")
        raise ValueError("BOT_TOKEN is not set")

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api_keys))  # This will capture API key input

    webhook_url = f"https://crypto-bot-3-white-wind-424.fly.dev/webhook/{token}"
    await application.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")

    config = Config()
    config.bind = ["0.0.0.0:8080"]
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(main())
