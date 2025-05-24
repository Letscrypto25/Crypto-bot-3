import base64
import json
import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler
from firebase_admin import credentials, db, initialize_app
from dotenv import load_dotenv
from datetime import datetime

from utils import send_alert, format_trade_message
from commands import (
    handle_command, start, help_command, trade, stop_autobot,
    get_leaderboard, set_base, set_platform, set_strategy,
    set_amount, show_config
)
from auto_bot import run_auto_bot
from database import get_user, get_autobot_status, create_user

# === Load Secrets from Environment ===
load_dotenv()
firebase_encoded = os.getenv("FIREBASE_CREDENTIALS_ENCODED")
firebase_url = os.getenv("FIREBASE_DATABASE_URL")
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
fly_app_name = os.getenv("FLY_APP_NAME")
authorized_user_id = int(os.getenv("AUTHORIZED_USER_ID", "0"))

# === Firebase Init ===

if not firebase_admin._apps:
    decoded = base64.b64decode(firebase_encoded).decode("utf-8")
    cred = credentials.Certificate(json.loads(decoded))
    initialize_app(cred, {"databaseURL": firebase_url})
    
# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Flask App ===
app = Flask(__name__)

# === Telegram App Init ===
application = Application.builder().token(bot_token).build()

# === Register Command Handlers ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("trade", trade))
application.add_handler(CommandHandler("stopautobot", stop_autobot))
application.add_handler(CommandHandler("leaderboard", get_leaderboard))
application.add_handler(CommandHandler("setbase", set_base))
application.add_handler(CommandHandler("setplatform", set_platform))
application.add_handler(CommandHandler("setstrategy", set_strategy))
application.add_handler(CommandHandler("setamount", set_amount))
application.add_handler(CommandHandler("showconfig", show_config))

# === Log Events to Firebase ===
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

# === Webhook Route ===
@app.route(f"/webhook/{bot_token}", methods=["POST"])
def telegram_webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.update_queue.put_nowait(update)
        return "ok"

# === Legacy Webhook Support ===
@app.route("/legacy/<token>", methods=["POST"])
def legacy_webhook(token):
    if token != bot_token:
        return {"ok": False, "error": "Unauthorized"}, 403

    data = request.get_json()
    if not data:
        return {"ok": False}

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

@app.route("/")
def index():
    return "Crypto Bot is live."

# === Start Webhook Listener ===
if __name__ == "__main__":
    logger.info("Starting Telegram bot webhook listener...")
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=f"https://{fly_app_name}.fly.dev/webhook/{bot_token}",
        flask_app=app
    )
