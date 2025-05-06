import os
import logging
import telegram
from telegram.ext import CommandHandler, Updater
import firebase_admin
from firebase_admin import credentials, db
from binance.client import Client
from flask import Flask
import threading

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Load Firebase credentials from environment path
firebase_cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")
if not firebase_cred_path:
    raise ValueError("FIREBASE_CREDENTIALS_PATH environment variable not set")
cred = credentials.Certificate(firebase_cred_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://your-firebase-url.firebaseio.com'  # <-- Replace with your actual URL
})

# Telegram Bot Token from env
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set")
bot = telegram.Bot(token=TOKEN)

# Flask app for Fly.io health check
app = Flask(__name__)

@app.route("/")
def health():
    return "Bot is running", 200

# Bot command: /start
def start(update, context):
    update.message.reply_text('Welcome to the Crypto Trading Bot! Use /setkeys to set your API keys.')

# /setkeys <binance_key> <binance_secret>
def setkeys(update, context):
    user_id = update.message.from_user.id
    try:
        binance_key = context.args[0]
        binance_secret = context.args[1]

        ref = db.reference(f'api_keys/{user_id}')
        ref.set({
            'binance_api_key': binance_key,
            'binance_api_secret': binance_secret,
        })

        update.message.reply_text("Your Binance API keys have been saved!")
    except IndexError:
        update.message.reply_text("Usage: /setkeys <binance_key> <binance_secret>")

# /status
def status(update, context):
    user_id = update.message.from_user.id
    ref = db.reference(f'api_keys/{user_id}')
    user_data = ref.get()

    if user_data:
        message = (
            f"Binance API Key: {'Set' if user_data.get('binance_api_key') else 'Not Set'}\n"
            f"Binance Secret: {'Set' if user_data.get('binance_api_secret') else 'Not Set'}"
        )
        update.message.reply_text(message)
    else:
        update.message.reply_text("No API keys found. Use /setkeys to add them.")

# /deletekeys
def deletekeys(update, context):
    user_id = update.message.from_user.id
    db.reference(f'api_keys/{user_id}').delete()
    update.message.reply_text("Your API keys have been deleted.")

# /trade
def trade(update, context):
    user_id = update.message.from_user.id
    ref = db.reference(f'api_keys/{user_id}')
    user_data = ref.get()

    if not user_data:
        update.message.reply_text("No API keys found. Use /setkeys first.")
        return

    try:
        binance = Client(user_data['binance_api_key'], user_data['binance_api_secret'])
        balance = binance.get_asset_balance(asset='USDT')
        binance_usdt = balance['free'] if balance else '0'
        update.message.reply_text(f"Binance USDT Balance: {binance_usdt}")
    except Exception as e:
        logger.error(f"Trade error: {e}")
        update.message.reply_text(f"Error: {str(e)}")

def run_bot():
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('setkeys', setkeys))
    dp.add_handler(CommandHandler('status', status))
    dp.add_handler(CommandHandler('deletekeys', deletekeys))
    dp.add_handler(CommandHandler('trade', trade))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=8080)
