import base64
import json
import os
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request
from utils import send_alert, format_trade_message
from commands import handle_command
from auto_bot import run_auto_bot 
from database import get_user, get_autobot_status, create_user
from datetime import datetime
from dotenv import load_dotenv
import requests

load_dotenv()

# === Load Secrets from Environment ===
firebase_encoded = os.getenv("FIREBASE_CREDENTIALS_ENCODED")
firebase_url = os.getenv("FIREBASE_DATABASE_URL")
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

if not bot_token:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is missing!")

print(f"[INFO] Bot token loaded: {bot_token[:10]}...")  # partial print for safety

# === Set Telegram Webhook ===
webhook_url = f"https://crypto-bot-3-white-wind-424.fly.dev/webhook/{bot_token}"
try:
    r = requests.get(f"https://api.telegram.org/bot{bot_token}/setWebhook?url={webhook_url}")
    print(f"[INFO] Webhook set: {r.json()}")
except Exception as e:
    print(f"[ERROR] Failed to set webhook: {e}")

# === Firebase Init ===
if not firebase_admin._apps:
    decoded = base64.b64decode(firebase_encoded).decode("utf-8")
    cred = credentials.Certificate(json.loads(decoded))
    firebase_admin.initialize_app(cred, {"databaseURL": firebase_url})

app = Flask(__name__)

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

@app.route("/webhook/<token>", methods=["POST"])
def telegram_webhook(token):
    if token != bot_token:
        print(f"[WARN] Invalid token in request: {token}")
        return {"ok": False, "error": "Unauthorized"}, 403
        
    data = request.get_json()
    if not data:
        print("[WARN] Empty request received.")
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
