import logging
import os
import asyncio
import json
from datetime import datetime
from base64 import b64encode

import firebase_admin
from firebase_admin import credentials, firestore

import httpx
from quart import Quart, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from hypercorn.asyncio import serve
from hypercorn.config import Config
from binance.client import AsyncClient

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Quart app
app = Quart(__name__)
application: Application = None
initialized = False

# Firebase initialization
firebase_cred = os.getenv("FIREBASE_CREDENTIALS")
if not firebase_cred:
    logger.error("FIREBASE_CREDENTIALS not set")
    raise ValueError("FIREBASE_CREDENTIALS not set")

try:
    cred_data = json.loads(firebase_cred)
    cred = credentials.Certificate(cred_data)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("Firebase initialized successfully.")
except json.JSONDecodeError:
    logger.error("Invalid JSON format for Firebase credentials.")
    raise
except Exception as e:
    logger.error(f"Error initializing Firebase: {e}")
    raise

# Health check
@app.route("/")
async def health_check():
    return "OK", 200

# Telegram webhook
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

# Luno auth
def get_luno_auth_header():
    key = os.getenv("LUNO_API_KEY")
    secret = os.getenv("LUNO_API_SECRET")
    auth = b64encode(f"{key}:{secret}".encode()).decode()
    return {"Authorization": f"Basic {auth}"}

# Luno balance
async def get_luno_balance():
    async with httpx.AsyncClient() as client:
        headers = get_luno_auth_header()
        resp = await client.get("https://api.luno.com/api/1/balance", headers=headers)
        if resp.status_code != 200:
            raise Exception("Luno API error")
        return resp.json()

# Binance balance
async def get_binance_balance():
    client = await AsyncClient.create(
        api_key=os.getenv("BINANCE_API_KEY"),
        api_secret=os.getenv("BINANCE_API_SECRET"),
    )
    account = await client.get_account()
    balances = [b for b in account['balances'] if float(b['free']) > 0]
    await client.close_connection()
    return balances

# Save user to Firestore
async def save_user(update: Update):
    user = update.effective_user
    user_ref = db.collection("users").document(str(user.id))

    user_data = {
        "telegram_id": user.id,
        "username": f"@{user.username}" if user.username else "unknown",
        "user_id": "Telegram api",
        "joined_at": datetime.utcnow(),
        "last_action": "start",
        "balance": 100,
        "subscribed": True,
    }

    user_ref.set(user_data, merge=True)

# Telegram commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save_user(update)
    await update.message.reply_text("Hello, I am your crypto trading bot!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /balance to view your Binance and Luno balances.")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        luno = await get_luno_balance()
        binance = await get_binance_balance()

        msg = "*Your Balances:*\n\n*Binance:*\n"
        for b in binance:
            msg += f"{b['asset']}: {b['free']}\n"

        msg += "\n*Luno:*\n"
        for w in luno['balance']:
            if float(w['balance']) > 0:
                msg += f"{w['asset']}: {w['balance']}\n"

        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Balance error: {e}")
        await update.message.reply_text(f"Error: {e}")

# Main function
async def main():
    global application
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN not set")
        raise ValueError("BOT_TOKEN is not set")

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("balance", balance_command))

    webhook_url = f"https://crypto-bot-3-white-wind-424.fly.dev/webhook/{token}"
    await application.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")

    config = Config()
    config.bind = ["0.0.0.0:8080"]
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(main())
