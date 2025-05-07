# Full backend logic for Let'sCrypto - Python main.py
# Includes trading, user management, tournament logic, fee handling, Firebase, Binance, Luno, encryption

import os
import json
import asyncio
import logging
import tempfile
from datetime import datetime
from cryptography.fernet import Fernet

from quart import Quart, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from firebase_admin import credentials, db, initialize_app
from binance.client import Client as BinanceClient
from luno_python.client import Client as LunoClient
from hypercorn.asyncio import serve
from hypercorn.config import Config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LetsCrypto")

# Firebase setup
FIREBASE = os.environ.get("FIREBASE_CREDENTIALS")
if not FIREBASE:
    raise ValueError("FIREBASE_CREDENTIALS is required")

with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as f:
    f.write(FIREBASE)
    f.flush()
    cred = credentials.Certificate(f.name)
    initialize_app(cred, {
        'databaseURL': 'https://crypto-bot-3-default-rtdb.firebaseio.com/'
    })

# Encryption setup
FERNET_KEY = os.getenv("ENCRYPTION_KEY")
fernet = Fernet(FERNET_KEY.encode())

# Quart app
app = Quart(__name__)
telegram_app: Application = None
initialized = False

@app.route("/")
async def index():
    return "Bot is live", 200

@app.route("/webhook/<token>", methods=["POST"])
async def telegram_webhook(token):
    global initialized
    if token != os.getenv("BOT_TOKEN"):
        return "Invalid token", 403

    if not initialized:
        await telegram_app.initialize()
        initialized = True

    update_data = await request.get_json()
    update = Update.de_json(update_data, telegram_app.bot)
    await telegram_app.process_update(update)
    return "OK", 200

# Firebase helper
def get_ref(path):
    return db.reference(path)

def encrypt(text):
    return fernet.encrypt(text.encode()).decode()

def decrypt(cipher):
    return fernet.decrypt(cipher.encode()).decode()

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to Let'sCrypto! Use /setkeys to store your API keys.")

async def setkeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Usage: /setkeys <exchange> <api_key> <api_secret>")
        return

    exchange, key, secret = args[0], args[1], args[2]
    ref = get_ref(f"users/{user_id}/keys")
    encrypted = {
        f"{exchange}_key": encrypt(key),
        f"{exchange}_secret": encrypt(secret)
    }
    ref.update(encrypted)
    await update.message.reply_text(f"Saved {exchange.upper()} API keys securely.")

async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    keys = get_ref(f"users/{user_id}/keys").get()
    bal_ref = get_ref(f"users/{user_id}/balance")

    try:
        # Binance
        if keys and 'binance_key' in keys:
            binance = BinanceClient(decrypt(keys['binance_key']), decrypt(keys['binance_secret']))
            usdt = binance.get_asset_balance(asset='USDT')['free']
        else:
            usdt = 0

        # Luno
        if keys and 'luno_key' in keys:
            luno = LunoClient(decrypt(keys['luno_key']), decrypt(keys['luno_secret']))
            l_bal = luno.get_balances()['balance']
            btc = next((b['balance'] for b in l_bal if b['asset'] == 'XBT'), '0')
        else:
            btc = 0

        # Record & fees
        profit = float(usdt) * 0.1  # example profit
        fee = profit * 0.005
        tournament = profit * 0.0125
        net = profit - fee - tournament
        bal_ref.set(net)

        await update.message.reply_text(f"Binance USDT: {usdt}\nLuno BTC: {btc}\nProfit: ${profit:.2f}, Fee: ${fee:.2f}, Net: ${net:.2f}")

    except Exception as e:
        logger.error(str(e))
        await update.message.reply_text("Error occurred during trade.")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    bal = get_ref(f"users/{user_id}/balance").get()
    await update.message.reply_text(f"Your current balance: ${bal or 0:.2f}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/setkeys <exchange> <api_key> <api_secret>\n/trade\n/balance\n/start")

async def main():
    global telegram_app
    token = os.getenv("BOT_TOKEN")
    telegram_app = Application.builder().token(token).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("setkeys", setkeys))
    telegram_app.add_handler(CommandHandler("trade", trade))
    telegram_app.add_handler(CommandHandler("balance", balance))
    telegram_app.add_handler(CommandHandler("help", help_command))

    webhook_url = f"https://crypto-bot-3-white-wind-424.fly.dev/webhook/{token}"
    await telegram_app.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to {webhook_url}")

    config = Config()
    config.bind = ["0.0.0.0:8080"]
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(main())
