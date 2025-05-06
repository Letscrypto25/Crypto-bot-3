import os
import logging
import asyncio
import json
import tempfile

import firebase_admin
from firebase_admin import credentials, db
from quart import Quart, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from binance.client import Client
from luno_python.client import Client as LunoClient
from hypercorn.asyncio import serve
from hypercorn.config import Config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Firebase credentials from env and write to a temp file
firebase_json = os.environ.get("FIREBASE_CREDENTIALS")
if not firebase_json:
    raise ValueError("FIREBASE_CREDENTIALS not set")

with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp:
    tmp.write(firebase_json)
    tmp.flush()
    cred = credentials.Certificate(tmp.name)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://crypto-bot-3-default-rtdb.firebaseio.com/'  # Replace if needed
    })

# Quart app for webhook
app = Quart(__name__)
telegram_app: Application = None
initialized = False

@app.route("/")
async def health():
    return "OK", 200

@app.route("/webhook/<token>", methods=["POST"])
async def telegram_webhook(token):
    global telegram_app, initialized
    if token != os.getenv("BOT_TOKEN"):
        return "Unauthorized", 403

    if not initialized:
        await telegram_app.initialize()
        initialized = True

    update_data = await request.get_json()
    update = Update.de_json(update_data, telegram_app.bot)
    await telegram_app.process_update(update)
    return "OK", 200

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Crypto Trading Bot! Use /setkeys to set your API keys.")

async def setkeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        binance_key, binance_secret, luno_key, luno_secret = context.args
        ref = db.reference(f'api_keys/{user_id}')
        ref.set({
            'binance_api_key': binance_key,
            'binance_api_secret': binance_secret,
            'luno_api_key': luno_key,
            'luno_api_secret': luno_secret
        })
        await update.message.reply_text("API keys saved!")
    except Exception:
        await update.message.reply_text("Usage: /setkeys <binance_key> <binance_secret> <luno_key> <luno_secret>")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ref = db.reference(f'api_keys/{user_id}')
    data = ref.get()
    if data:
        msg = "\n".join([
            f"Binance API Key: {'Set' if data.get('binance_api_key') else 'Not Set'}",
            f"Binance Secret: {'Set' if data.get('binance_api_secret') else 'Not Set'}",
            f"Luno API Key: {'Set' if data.get('luno_api_key') else 'Not Set'}",
            f"Luno Secret: {'Set' if data.get('luno_api_secret') else 'Not Set'}"
        ])
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("No API keys found. Use /setkeys.")

async def deletekeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.reference(f'api_keys/{user_id}').delete()
    await update.message.reply_text("Your keys have been deleted.")

async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = db.reference(f'api_keys/{user_id}').get()
    if not data:
        await update.message.reply_text("No API keys found. Use /setkeys.")
        return
    try:
        binance = Client(data['binance_api_key'], data['binance_api_secret'])
        b_usdt = binance.get_asset_balance(asset='USDT')['free']
        luno = LunoClient(data['luno_api_key'], data['luno_api_secret'])
        luno_balances = luno.get_balances()['balance']
        l_bal = "\n".join(f"{b['asset']}: {b['balance']}" for b in luno_balances)
        await update.message.reply_text(f"Binance USDT: {b_usdt}\nLuno:\n{l_bal}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# Async main function
async def main():
    global telegram_app
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN not set")

    telegram_app = Application.builder().token(token).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("setkeys", setkeys))
    telegram_app.add_handler(CommandHandler("status", status))
    telegram_app.add_handler(CommandHandler("deletekeys", deletekeys))
    telegram_app.add_handler(CommandHandler("trade", trade))

    # Set webhook
    webhook_url = f"https://crypto-bot-3-white-wind-424.fly.dev/webhook/{token}"
    await telegram_app.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to {webhook_url}")

    # Run Quart server
    config = Config()
    config.bind = ["0.0.0.0:8080"]
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(main())
