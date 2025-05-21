import os import json import logging import base64 from flask import Flask, request, jsonify, send_file import firebase_admin from datetime import datetime from firebase_admin import credentials, initialize_app, db from celery import Celery from utils import send_telegram_message  # Make sure this handles sending msgs via Telegram API from exchange import get_binance_prices, get_luno_prices  # Assumes your exchange API logic is modular

Setup logging

logging.basicConfig(level=logging.INFO) logger = logging.getLogger(name)

Initialize Flask app

app = Flask(name)

Load secrets from environment variables

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") if not BOT_TOKEN: logger.error("Missing TELEGRAM_BOT_TOKEN in environment variables!") exit(1)

try: USER_ID = int(os.environ.get("TELEGRAM_USER_ID")) except Exception: logger.error("Invalid or missing TELEGRAM_USER_ID in environment variables!") exit(1)

FIREBASE_ENCODED = os.environ.get("FIREBASE_CREDENTIALS_ENCODED") if not FIREBASE_ENCODED: logger.error("Missing FIREBASE_CREDENTIALS_ENCODED in environment variables!") exit(1)

Decode and initialize Firebase

try: decoded = base64.b64decode(FIREBASE_ENCODED) creds_dict = json.loads(decoded) cred = credentials.Certificate(creds_dict) try: firebase_app = firebase_admin.get_app() except ValueError: firebase_app = initialize_app(cred, { 'databaseURL': f'https://Crypto-bot-3.firebaseio.com' }) db_root = db.reference("/") logger.info("Firebase initialized successfully.") except Exception as e: logger.error(f"Failed to initialize Firebase: {e}") exit(1)

Setup Celery

CELERY_BROKER = os.environ.get("REDIS_URL", "redis://localhost:6379/0") celery = Celery(name, broker=CELERY_BROKER) celery.conf.update(result_backend=CELERY_BROKER)

Flask secret key

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-please")

Util functions

def is_registered(user_id): try: user_ref = db_root.child("users").child(str(user_id)) return user_ref.get() is not None except Exception as e: logger.error(f"Firebase read error in is_registered: {e}") return False

def register_user(user_id, user_info): try: db_root.child("users").child(str(user_id)).set(user_info) logger.info(f"User {user_id} registered successfully.") except Exception as e: logger.error(f"Firebase write error in register_user: {e}")

Command handler

def handle_command(text, user_id): if not text: return "Hey, I didn't catch that. Try /help for commands."

text = text.strip().lower()

if text == "/start":
    if not is_registered(user_id):
        user_info = {"id": user_id, "joined_at": int(datetime.utcnow().timestamp())}
        register_user(user_id, user_info)
        return "Welcome to Let'sCrypto! Chill and explore the commands."
    return "Welcome back! Use /help to see what I can do."

if not is_registered(user_id):
    return "Send /start first to register."

if text == "/help":
    return ("Available commands:\n"
            "/start - Register or restart\n"
            "/help - Show this menu\n"
            "/status - Bot status\n"
            "/trigger - Run trading bot\n"
            "/binance - Get Binance prices\n"
            "/luno - Get Luno prices")

if text == "/status":
    return "Bot is alive and well."

if text == "/trigger":
    from tasks import run_auto_bot_task
    run_auto_bot_task.delay({"source": "manual_trigger", "user_id": user_id})
    return "Trading task triggered."

if text == "/binance":
    try:
        data = get_binance_prices()
        return json.dumps(data, indent=2)
    except Exception as e:
        logger.error(f"Binance fetch error: {e}")
        return "Couldn't fetch Binance data."

if text == "/luno":
    try:
        data = get_luno_prices()
        return json.dumps(data, indent=2)
    except Exception as e:
        logger.error(f"Luno fetch error: {e}")
        return "Couldn't fetch Luno data."

return f"Unknown command '{text}'. Try /help."

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"]) def telegram_webhook(): try: data = request.get_json() if not data or "message" not in data: return jsonify({"ok": True})

message = data["message"]
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")

    response = handle_command(text, user_id=user_id)
    send_telegram_message(chat_id, response)
except Exception as e:
    logger.exception("Error in webhook")
    send_telegram_message(USER_ID, f"Bot error: {e}")
return jsonify({"ok": True})

@app.route("/", methods=["GET"]) def health_check(): return jsonify({"status": "ok"}), 200

Add other routes (trigger, test endpoints, manifest, etc) below as needed

if name == "main": port = int(os.getenv("PORT", 8080)) debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true" app.run(host="0.0.0.0", port=port, debug=debug_mode)

