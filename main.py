import base64
import asyncio
import json
import os
import logging
from handlers import login
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler
from firebase_admin import credentials, db, initialize_app
from dotenv import load_dotenv
from datetime import datetime
import firebase_admin
from urllib.parse import unquote
from fastapi.security import HTTPBearer

# Import your strategy loop
from strategy_loop import strategy_loop

from commands.start import start
from commands import *
from commands.trade import trade
from commands.autobot import autobot, start_autobot
from commands.leaderboard import leaderboard
from commands.setbase import setbase
from commands.setplatform import setplatform
from commands.setstrategy import setstrategy
from commands.setamount import setamount
from commands.showconfig import showconfig
from commands.balance import balance
from commands.register import register

from utils import send_alert, format_trade_message
from database import get_user, get_autobot_status, create_user

# === Load Environment Variables ===
load_dotenv()
firebase_encoded = os.getenv("FIREBASE_CREDENTIALS_ENCODED")
firebase_url = os.getenv("FIREBASE_DATABASE_URL")
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
fly_app = "crypto-bot-3-white-wind-424"

# === Firebase Init ===
if not firebase_admin._apps:
    decoded = base64.b64decode(firebase_encoded).decode("utf-8")
    cred = credentials.Certificate(json.loads(decoded))
    initialize_app(cred, {"databaseURL": firebase_url})

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crypto-bot")

# === FastAPI App ===
app = FastAPI()
security = HTTPBearer()

# === Telegram Bot Init ===
telegram_app = Application.builder().token(bot_token).build()

# === Register Handlers for all commands ===
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("trade", trade))
telegram_app.add_handler(CommandHandler("start_autobot", start_autobot))
telegram_app.add_handler(CommandHandler("leaderboard", leaderboard))
telegram_app.add_handler(CommandHandler("setbase", setbase))
telegram_app.add_handler(CommandHandler("setplatform", setplatform))
telegram_app.add_handler(CommandHandler("setstrategy", setstrategy))
telegram_app.add_handler(CommandHandler("setamount", setamount))
telegram_app.add_handler(CommandHandler("showconfig", showconfig))
telegram_app.add_handler(CommandHandler("register", register))
telegram_app.add_handler(CommandHandler("login", login))
telegram_app.add_handler(CommandHandler("balance", balance))
telegram_app.add_handler(CommandHandler("autobot", autobot))

# === Firebase Logging ===
def log_event(user_id, event_type, message_text, status="ok", error=None):
    log_ref = db.reference(f"logs/{user_id}")
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_type,
        "message": message_text,
        "status": status,
    }
    if error:
        log_entry["error"] = str(error)
    log_ref.push(log_entry)

# === Telegram Webhook Endpoint ===
@app.post("/webhook/{token}")
async def telegram_webhook(request: Request, token: str):
    token = unquote(token)
    if token != bot_token:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=400, detail="Invalid Telegram update")

    return {"ok": True}

# === Root Endpoint ===
@app.get("/")
def root():
    return {"message": "Crypto Bot is live"}

# === Startup Event ===
@app.on_event("startup")
async def start_bot():
    logger.info("Starting Telegram bot...")
    await telegram_app.initialize()

    await telegram_app.bot.set_my_commands([
        ("start", "Start the bot"),
        ("help", "Show help info"),
        ("trade", "Execute a manual trade"),
        ("stopautobot", "Stop the auto trading bot"),
        ("leaderboard", "Show the leaderboard"),
        ("setbase", "Set your base currency"),
        ("setplatform", "Choose Luno or Binance"),
        ("setstrategy", "Select your strategy"),
        ("setamount", "Set trade amount"),
        ("showconfig", "View your current configuration"),
        ("register", "Register a new account"),
        ("login", "Log into your account"),
        ("balance", "Check your crypto balance"),
    ])

    await telegram_app.bot.set_webhook(
        url=f"https://{fly_app}.fly.dev/webhook/{bot_token}"
    )
    logger.info("Webhook set successfully.")

    # Start strategy loop as background task
    asyncio.create_task(strategy_loop())

# === Shutdown Event ===
@app.on_event("shutdown")
async def stop_bot():
    logger.info("Stopping Telegram bot...")
    await telegram_app.shutdown()
