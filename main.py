import os
import logging
import telegram
from telegram.ext import CommandHandler, Updater
import firebase_admin
from firebase_admin import credentials, db
from binance.client import Client as BinanceClient
from luno_python.client import Client as LunoClient
import requests

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Load Firebase credentials from environment path
firebase_cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")
if not firebase_cred_path:
    raise ValueError("FIREBASE_CREDENTIALS_PATH environment variable not set")

cred = credentials.Certificate(firebase_cred_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://your-firebase-url.firebaseio.com'  # Replace with your Firebase URL
})

# Telegram Bot Token from environment
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set")

bot = telegram.Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Command: /start
def start(update, context):
    update.message.reply_text('Welcome to the Crypto Trading Bot! Use /setkeys to set your API keys.')

# Command: /setkeys <binance_key> <binance_secret> <luno_key> <luno_secret>
def setkeys(update, context):
    user_id = update.message.from_user.id
    try:
        binance_key = context.args[0]
        binance_secret = context.args[1]
        luno_key = context.args[2]
        luno_secret = context.args[3]

        ref = db.reference(f'api_keys/{user_id}')
        ref.set({
            'binance_api_key': binance_key,
            'binance_api_secret': binance_secret,
            'luno_api_key': luno_key,
            'luno_api_secret': luno_secret
        })

        update.message.reply_text("Your API keys have been saved successfully!")
    except IndexError:
        update.message.reply_text("Usage: /setkeys <binance_key> <binance_secret> <luno_key> <luno_secret>")

# Command: /status
def status(update, context):
    user_id = update.message.from_user.id
    ref = db.reference(f'api_keys/{user_id}')
    user_data = ref.get()

    if user_data:
        message = (
            f"Binance API Key: {'Set' if user_data.get('binance_api_key') else 'Not Set'}\n"
            f"Binance Secret: {'Set' if user_data.get('binance_api_secret') else 'Not Set'}\n"
            f"Luno API Key: {'Set' if user_data.get('luno_api_key') else 'Not Set'}\n"
            f"Luno Secret: {'Set' if user_data.get('luno_api_secret') else 'Not Set'}"
        )
        update.message.reply_text(message)
    else:
        update.message.reply_text("No API keys found. Use /setkeys to add them.")

# Command: /getkeys (shows full keys - use with caution)
def getkeys(update, context):
    user_id = update.message.from_user.id
    ref = db.reference(f'api_keys/{user_id}')
    user_data = ref.get()

    if user_data:
        update.message.reply_text(
            f"Binance Key: {user_data.get('binance_api_key')}\n"
            f"Binance Secret: {user_data.get('binance_api_secret')}\n"
            f"Luno Key: {user_data.get('luno_api_key')}\n"
            f"Luno Secret: {user_data.get('luno_api_secret')}"
        )
    else:
        update.message.reply_text("No API keys found.")

# Register commands
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("setkeys", setkeys))
dispatcher.add_handler(CommandHandler("status", status))
dispatcher.add_handler(CommandHandler("getkeys", getkeys))

# Start bot
updater.start_polling()
updater.idle()
