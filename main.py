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

# === Handle Command for Legacy Webhook ===
async def handle_command(text, user_id, chat_id):
    command = text.strip().split()[0].lower()
    context_args = text.strip().split()[1:]

    class DummyContext:
        def __init__(self, args):
            self.args = args

    class DummyUpdate:
        def __init__(self, user_id, chat_id):
            self.effective_user = type("User", (), {"id": int(user_id)})
            self.effective_chat = type("Chat", (), {"id": int(chat_id)})
            self.message = type("Message", (), {"text": text})

    update = DummyUpdate(user_id, chat_id)
    context = DummyContext(context_args)

    command_map = {
        "/start": start,
        "/help": help_command,
        "/trade": trade,
        "/stopautobot": stop_autobot,
        "/leaderboard": get_leaderboard,
        "/setbase": set_base,
        "/setplatform": set_platform,
        "/setstrategy": set_strategy,
        "/setamount": set_amount,
        "/showconfig": show_config
    }

    handler = command_map.get(command)
    if handler:
        await handler(update, context)
        return f"Executed {command}"
    return "Unknown command."

# === Telegram Webhook Route with token decoding ===
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

# === Fallback Legacy Webhook ===
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
            response = await handle_command(text, user_id, chat_id)
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

    return {"ok": True}

# === Root Endpoint ===
@app.get("/")
def root():
    return {"message": "Crypto Bot is live"}

# === Start bot background service on app startup ===
@app.on_event("startup")
async def start_bot():
    logger.info("Setting Telegram webhook...")
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(
        url=f"https://{fly_app}.fly.dev/webhook/{bot_token}"
    )
    logger.info("Webhook set successfully.")
