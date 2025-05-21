import base64
import json
import os
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request
from utils import send_alert, format_trade_message
from commands import handle_command
from auto_bot import auto_bot_logic

# Load secrets from environment
firebase_encoded = os.getenv("FIREBASE_CREDENTIALS_ENCODED")
firebase_url = os.getenv("FIREBASE_DATABASE_URL")
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

# Firebase Init
if not firebase_admin._apps:
    decoded = base64.b64decode(firebase_encoded).decode("utf-8")
    cred = credentials.Certificate(json.loads(decoded))
    firebase_admin.initialize_app(cred, {"databaseURL": firebase_url})

# Flask App for Telegram Webhook
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        if text.startswith("/"):
            response = handle_command(text)
            send_alert(response)
    return {"ok": True}

@app.route("/")
def index():
    return "Crypto Bot is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
