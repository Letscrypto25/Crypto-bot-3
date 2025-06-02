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
from handlers.login import login
from commands.start import start_command
from commands.help import help_command
from commands.trade import trade_command
#from commands.start_autobot import start_autobot_command
from commands.leaderboard import leaderboard_command
from commands.setbase import setbase_command
from commands.setplatform import setplatform_command
from commands.setstrategy import setstrategy_command
from commands.setamount import setamount_command
from commands.showconfig import showconfig_command
from commands.balance import balance_command
from commands.register import register_command# ✅ FIXED: direct function import

from utils import send_alert, format_trade_message
from commands.autobot import autobot_command  # ✅ import the function
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
telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("trade", trade_command))
#telegram_app.add_handler(CommandHandler("start_autobot", start_autobot_command))
telegram_app.add_handler(CommandHandler("leaderboard", leaderboard_command))
telegram_app.add_handler(CommandHandler("setbase", setbase_command))
telegram_app.add_handler(CommandHandler("setplatform", setplatform_command))
telegram_app.add_handler(CommandHandler("setstrategy", setstrategy_command))
telegram_app.add_handler(CommandHandler("setamount", setamount_command))
telegram_app.add_handler(CommandHandler("showconfig", showconfig_command))
telegram_app.add_handler(CommandHandler("register", register_command))
telegram_app.add_handler(CommandHandler("login", login_command))
telegram_app.add_handler(CommandHandler("balance", balance_command))  # ✅ fixed
telegram_app.add_handler(CommandHandler("autobot", autobot_command))  # ✅

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

# === Combined Telegram Webhook with legacy logic ===
@app.post("/webhook/{token}")
async def telegram_webhook(request: Request, token: str):
    token = unquote(token)
    if token != bot_token:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse JSON from webhook request: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    try:
        if "update_id" in data:
            update = Update.de_json(data, telegram_app.bot)
            await telegram_app.process_update(update)
        else:
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
                    send_alert(f"Command error for user {user_id}: {e}", chat_id)
                    send_alert("Oops, there was an error handling your command.", chat_id)
                    log_event(user_id, "command", text, status="error", error=e)
                return {"ok": True}

            try:
                if get_autobot_status(user_id):
                    run_auto_bot(user_id)
                    log_event(user_id, "autobot", text)
            except Exception as e:
                send_alert(f"AutoBot error for {user_id}: {e}", chat_id)
                send_alert("Error running AutoBot. Check your settings.", chat_id)
                log_event(user_id, "autobot", text, status="error", error=e)

    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=400, detail="Invalid Telegram update")

    return {"ok": True}

@app.get("/")
def root():
    return {"message": "Crypto Bot is live"}

@app.on_event("startup")
async def start_bot():
    logger.info("Starting Telegram bot...")
    await telegram_app.initialize()

    # Set all commands for Telegram UI
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

    # Start your strategy loop as a background task on startup
    asyncio.create_task(strategy_loop())

@app.on_event("shutdown")
async def stop_bot():
    logger.info("Stopping Telegram bot...")
    await telegram_app.shutdown()
