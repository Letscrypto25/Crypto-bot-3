import os
import json
import logging
import base64
from flask import Flask, request, jsonify, send_file
import firebase_admin
from firebase_admin import credentials, initialize_app, db
from celery import Celery
from utils import send_telegram_message, is_valid_user
from tasks import run_auto_bot_task

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Load secrets from environment variables
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("Missing TELEGRAM_BOT_TOKEN in environment variables!")
    exit(1)

try:
    USER_ID = int(os.environ.get("TELEGRAM_USER_ID"))
except Exception:
    logger.error("Invalid or missing TELEGRAM_USER_ID in environment variables!")
    exit(1)

FIREBASE_ENCODED = os.environ.get("FIREBASE_CREDENTIALS_ENCODED")
if not FIREBASE_ENCODED:
    logger.error("Missing FIREBASE_CREDENTIALS_ENCODED in environment variables!")
    exit(1)

# Decode and initialize Firebase
try:
    decoded = base64.b64decode(FIREBASE_ENCODED)
    creds_dict = json.loads(decoded)
    cred = credentials.Certificate(creds_dict)
    try:
        firebase_app = firebase_admin.get_app()
    except ValueError:
        firebase_app = initialize_app(cred, {
            'databaseURL': f'https://{creds_dict["project_id"]}.firebaseio.com'
        })
    db_root = db.reference("/")
    logger.info("Firebase initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {e}")
    exit(1)

# Setup Celery
CELERY_BROKER = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
celery = Celery(__name__, broker=CELERY_BROKER)
celery.conf.update(result_backend=CELERY_BROKER)

# Flask secret key (for sessions etc)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-please")

# --- Helper: Command handler stub ---
def handle_command(text, user_id):
    """
    Your command handler logic here.
    Return a string response to send back to user.
    """
    # Example simple command handling
    if not text:
        return "No command received."

    text = text.strip().lower()
    if text == "/start":
        return "Welcome! Bot is up and running."
    elif text == "/help":
        return "Available commands: /start, /help, /status, /trigger"
    elif text == "/status":
        return "All systems operational."
    elif text == "/trigger":
        run_auto_bot_task.delay({"source": "manual_trigger", "user_id": user_id})
        return "Bot task triggered."
    else:
        return f"Unknown command: {text}"

# --- Telegram Webhook route ---
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json()
        logger.info("Update received: %s", json.dumps(data))

        if not data or "message" not in data:
            return jsonify({"ok": True})

        message = data["message"]
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        text = message.get("text", "")

        if not is_valid_user(user_id):
            send_telegram_message(chat_id, "Access denied.")
            return jsonify({"ok": True})

        response = handle_command(text, user_id=user_id)
        send_telegram_message(chat_id, response)

    except Exception as e:
        logger.exception("Error processing webhook update")
        # Notify admin/user about the error
        send_telegram_message(USER_ID, f"Bot error: {e}")

    return jsonify({"ok": True})

# --- Health check endpoint ---
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

# --- Start bot task endpoint (trigger Celery task manually) ---
@app.route("/start_bot", methods=["GET"])
def start_bot_route():
    run_auto_bot_task.delay()
    return jsonify({"status": "bot started"}), 200

# --- Manual trigger via POST with optional data ---
@app.route("/trigger", methods=["POST"])
def trigger_task():
    try:
        content = request.json or {}
        run_auto_bot_task.delay(content)
        return jsonify({"status": "manual trigger received"}), 202
    except Exception as e:
        logger.error(f"Trigger task error: {e}")
        return jsonify({"error": str(e)}), 500

# --- Firebase test endpoints ---
@app.route("/test_write", methods=["GET"])
def test_write():
    try:
        test_data = {
            "timestamp": db.SERVER_TIMESTAMP,
            "message": "Test write from Flask"
        }
        db_root.child("test_node").push(test_data)
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"Firebase write failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/test_read", methods=["GET"])
def test_read():
    try:
        result = db_root.child("test_node").get()
        return jsonify({"data": result}), 200
    except Exception as e:
        logger.error(f"Firebase read failed: {e}")
        return jsonify({"error": str(e)}), 500

# --- Send test Telegram message ---
@app.route("/send_test", methods=["GET"])
def send_test_message():
    try:
        send_telegram_message(USER_ID, "Test message from /send_test endpoint.")
        return jsonify({"sent": True}), 200
    except Exception as e:
        logger.error(f"Send test message failed: {e}")
        return jsonify({"error": str(e)}), 500

# --- Celery test endpoint ---
@app.route("/test_celery", methods=["GET"])
def test_celery():
    try:
        run_auto_bot_task.delay({"source": "manual_test"})
        return jsonify({"status": "celery triggered"}), 200
    except Exception as e:
        logger.error(f"Celery test error: {e}")
        return jsonify({"error": str(e)}), 500

# --- AI Plugin manifest endpoint ---
@app.route("/.well-known/ai-plugin.json", methods=["GET"])
def plugin_manifest():
    return jsonify({
        "schema_version": "v1",
        "name_for_model": "crypto_trading_bot",
        "name_for_human": "Crypto Trading Bot",
        "description_for_model": "Bot to trade and monitor Binance and Luno.",
        "description_for_human": "Trade monitoring and automation for Binance & Luno.",
        "auth": {"type": "none"},
        "api": {"type": "openapi", "url": "/openapi.yaml"},
        "logo_url": "/static/logo.png",
        "contact_email": "support@yourdomain.com",
        "legal_info_url": "https://yourdomain.com/legal"
    })

# --- Serve OpenAPI spec ---
@app.route("/openapi.yaml", methods=["GET"])
def openapi_spec():
    try:
        return send_file("openapi.yaml")
    except Exception as e:
        logger.error(f"OpenAPI spec not found: {e}")
        return jsonify({"error": "OpenAPI spec not found"}), 404

# --- Serve static files ---
@app.route("/static/<path:filename>", methods=["GET"])
def static_files(filename):
    try:
        return send_file(f"static/{filename}")
    except Exception as e:
        logger.error(f"Static file not found: {e}")
        return jsonify({"error": "Static file not found"}), 404

# --- App entrypoint ---
if __name__ == "__main__":
    # For local dev/testing:
    # Use PORT env var or default 8080
    # Debug True for dev only! Disable in prod
    port = int(os.getenv("PORT", 8080))
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
