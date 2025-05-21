import base64
import json
import os
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request
from utils import send_alert, send_message, format_trade_message
from commands import handle_command
from auto_bot import auto_bot_logic
from database import get_user, get_autobot_status

# === Load Secrets from Environment ===
firebase_encoded = os.getenv("FIREBASE_CREDENTIALS_ENCODED")
firebase_url = os.getenv("FIREBASE_DATABASE_URL")
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

# === Firebase Init ===
if not firebase_admin._apps:
    decoded = base64.b64decode(firebase_encoded).decode("utf-8")
    cred = credentials.Certificate(json.loads(decoded))
    firebase_admin.initialize_app(cred, {"databaseURL": firebase_url})

# === Flask App for Telegram Webhook ===
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
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

    # === Handle New User ===
    if not user:
        from database import create_user
        create_user(user_id)
        send_message(chat_id, "Welcome! Your crypto bot profile has been created.")
        return {"ok": True}

    # === Handle Commands ===
    if text.startswith("/"):
        try:
            response = handle_command(text, user_id)
            if response:
                send_message(chat_id, response)
        except Exception as e:
            send_alert(f"Command error for user {user_id}: {e}")
            send_message(chat_id, "Oops, there was an error handling your command.")
        return {"ok": True}

    # === Run AutoBot Logic if Enabled ===
    try:
        if get_autobot_status(user_id):
            auto_bot_logic(user_id)
    except Exception as e:
        send_alert(f"AutoBot error for {user_id}: {e}")
        send_message(chat_id, "Error running AutoBot. Check your settings.")

    return {"ok": True}

@app.route("/")
def index():
    return "Crypto Bot is live."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
