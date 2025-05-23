import base64 import json import os from datetime import datetime

import firebase_admin from firebase_admin import credentials, db from flask import Flask, request from dotenv import load_dotenv import requests

from utils import send_alert, format_trade_message from commands import handle_command from auto_bot import run_auto_bot from database import get_user, get_autobot_status, create_user

=== Load environment ===

load_dotenv() firebase_encoded = os.getenv("FIREBASE_CREDENTIALS_ENCODED") firebase_url = os.getenv("FIREBASE_DATABASE_URL") bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

if not bot_token: raise ValueError("TELEGRAM_BOT_TOKEN environment variable is missing!")

print(f"[INFO] Bot token loaded: {bot_token[:10]}...")

=== Set Telegram webhook ===

webhook_url = f"https://crypto-bot-3-white-wind-424.fly.dev/webhook/{bot_token}" try: r = requests.get(f"https://api.telegram.org/bot{bot_token}/setWebhook?url={webhook_url}") print(f"[INFO] Webhook set response: {r.json()}") except Exception as e: print(f"[ERROR] Failed to set webhook: {e}")

=== Firebase init ===

if not firebase_admin._apps: decoded = base64.b64decode(firebase_encoded).decode("utf-8") cred = credentials.Certificate(json.loads(decoded)) firebase_admin.initialize_app(cred, {"databaseURL": firebase_url})

app = Flask(name)

def log_event(user_id, event_type, message_text, status="ok", error=None): try: log_ref = db.reference(f"logs/{user_id}") log_entry = { "timestamp": datetime.utcnow().isoformat(), "event": event_type, "message": message_text, "status": status, } if error: log_entry["error"] = str(error) log_ref.push(log_entry) except Exception as e: print(f"[ERROR] Failed to log event for user {user_id}: {e}")

@app.route("/webhook/<token>", methods=["POST"]) def telegram_webhook(token): print(f"[DEBUG] Token in URL: {token}") if token != bot_token: print(f"[WARN] Invalid token received.") return {"ok": False, "error": "Unauthorized"}, 403

data = request.get_json()
if not data:
    print("[WARN] Empty or invalid JSON in request.")
    return {"ok": False}

message = data.get("message", {})
chat_id = message.get("chat", {}).get("id")
text = message.get("text", "").strip()

if not chat_id:
    print("[WARN] No chat_id found in message.")
    return {"ok": False}

user_id = str(chat_id)

# Ensure user exists
try:
    user = get_user(user_id)
    if not user:
        create_user(user_id)
        send_alert("Welcome! Your crypto bot profile has been created.", chat_id)
        log_event(user_id, "new_user", text)
        return {"ok": True}
except Exception as e:
    send_alert("Error initializing your user profile.", chat_id)
    log_event(user_id, "init_error", text, status="error", error=e)
    return {"ok": False}

# Command handler
if text.startswith("/"):
    try:
        response = handle_command(text, user_id)
        if response:
            send_alert(response, chat_id)
        else:
            send_alert("No response from command. Please try again.", chat_id)
        log_event(user_id, "command", text)
    except Exception as e:
        send_alert(f"Command error: {e}", chat_id)
        log_event(user_id, "command", text, status="error", error=e)
    return {"ok": True}

# AutoBot run if not a command
try:
    if get_autobot_status(user_id):
        result = run_auto_bot(user_id)
        send_alert(result or "AutoBot ran with no update.", chat_id)
        log_event(user_id, "autobot", text)
    else:
        send_alert("AutoBot is currently disabled. Use /startautobot to enable it.", chat_id)
except Exception as e:
    send_alert(f"AutoBot error: {e}", chat_id)
    log_event(user_id, "autobot", text, status="error", error=e)

return {"ok": True}

@app.route("/") def index(): return "Crypto Bot is live."

if name == "main": app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

