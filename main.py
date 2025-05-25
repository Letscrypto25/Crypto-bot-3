# === IMPORTS ===
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
from database import get_user, get_autobot_status, create_user, update_user_config

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

# === Register Handlers ===
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

# === Telegram Webhook Route ===
@app.post("/webhook/{token}")
async def telegram_webhook(request: Request, token: str):
    token = unquote(token)
    if token != bot_token:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.update_queue.put_nowait(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail="Invalid Telegram update")

# === Legacy Webhook ===
@app.post("/legacy/{token}")
async def legacy_webhook(token: str, request: Request):
    if token != bot_token:
        raise HTTPException(status_code=403, detail="Unauthorized")

    data = await request.json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id:
        return {"ok": False}

    user_id = str(chat_id)
    user = get_user(user_id)

    if not user:
        create_user(user_id)
        send_alert("Welcome! Your crypto bot profile has been created.", chat_id)
        log_event(user_id, "new_user", text)
        return {"ok": True}

    if text.startswith("/"):
        try:
            response = handle_command(text, user_id)
            if response:
                send_alert(response, chat_id)
            log_event(user_id, "command", text)
        except Exception as e:
            send_alert(f"Command error for user {user_id}: {e}")
            send_alert("Oops, there was an error handling your command.", chat_id)
            log_event(user_id, "command", text, status="error", error=e)
        return {"ok": True}

    try:
        if get_autobot_status(user_id):
            run_auto_bot(user_id)
            log_event(user_id, "autobot", text)
    except Exception as e:
        send_alert(f"AutoBot error for {user_id}: {e}")
        send_alert("Error running AutoBot. Check your settings.", chat_id)
        log_event(user_id, "autobot", text, status="error", error=e)

    return {"ok": True}

# === Register New User via API ===
@app.post("/register")
async def register_user(request: Request):
    data = await request.json()
    user_id = str(data.get("user_id"))
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    if get_user(user_id):
        return {"status": "exists", "message": f"User {user_id} already registered."}

    create_user(user_id)
    log_event(user_id, "register_api", "User registered via API")
    return {"status": "created", "message": f"User {user_id} successfully registered."}

# === Manual Trade via API ===
@app.post("/api/trade")
async def trade_api(request: Request):
    data = await request.json()
    user_id = str(data.get("user_id"))
    amount = data.get("amount")

    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # If amount is passed, update config
        if amount:
            update_user_config(user_id, {"amount": amount})
        run_auto_bot(user_id, manual=True)
        log_event(user_id, "api_trade", f"Trade executed via API for {user_id}")
        return {"status": "success", "message": "Trade executed"}
    except Exception as e:
        log_event(user_id, "api_trade", "Error", status="error", error=e)
        raise HTTPException(status_code=500, detail=f"Trade error: {e}")

# === Root Endpoint ===
@app.get("/")
def root():
    return {"message": "Crypto Bot is live"}

# === Startup Event ===
@app.on_event("startup")
async def start_bot():
    logger.info("Starting Telegram bot...")
    await telegram_app.initialize()
    await telegram_app.start()

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
    ])

    await telegram_app.bot.set_webhook(
        url=f"https://{fly_app}.fly.dev/webhook/{bot_token}"
    )
    logger.info("Webhook set successfully.")

# === Shutdown Event ===
@app.on_event("shutdown")
async def stop_bot():
    logger.info("Stopping Telegram bot...")
    await telegram_app.shutdown()
