import base64
import json
import os
import logging
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler
from firebase_admin import credentials, db, initialize_app
from dotenv import load_dotenv
from datetime import datetime
import firebase_admin
from urllib.parse import unquote

from utils import send_alert, format_trade_message
from commands import (
    start, help_command, trade, stop_autobot,
    get_leaderboard, set_base, set_platform, set_strategy,
    set_amount, show_config
)
from auto_bot import run_auto_bot
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

# === Telegram Bot Init ===
telegram_app = Application.builder().token(bot_token).build()

# === Register Command Handlers ===
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("trade", trade))
telegram_app.add_handler(CommandHandler("stopautobot", stop_autobot))
telegram_app.add_handler(CommandHandler("leaderboard", get_leaderboard))
telegram_app.add_handler(CommandHandler("setbase", set_base))
telegram_app.add_handler(CommandHandler("setplatform", set_platform))
telegram_app.add_handler(CommandHandler("setstrategy", set_strategy))
telegram_app.add_handler(CommandHandler("setamount", set_amount))
telegram_app.add_handler(CommandHandler("showconfig", show_config))

# === Firebase Logging Helper ===
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
        await telegram_app.update_queue.put(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail="Invalid Telegram update")

# === Legacy Webhook Fallback (Now Standardized) ===
@app.post("/legacy/{token}")
async def legacy_webhook(token: str, request: Request):
    if token != bot_token:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.update_queue.put(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Legacy webhook error: {e}")
        raise HTTPException(status_code=400, detail="Invalid Telegram update")

# === Root Check Endpoint ===
@app.get("/")
def root():
    return {"message": "Crypto Bot is live"}

# === Startup Task ===
@app.on_event("startup")
async def start_bot():
    logger.info("Initializing Telegram bot...")
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(
        url=f"https://{fly_app}.fly.dev/webhook/{bot_token}"
    )
    logger.info("Webhook set successfully.")
