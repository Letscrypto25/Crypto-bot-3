import os
import json
import logging
import base64
from flask import Flask, request, jsonify, send_file
from firebase_admin import credentials, initialize_app, db
from utils import send_telegram_message, is_valid_user
from tasks import run_auto_bot_task
from celery import Celery

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Load secrets directly from environment variables
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
USER_ID = int(os.environ.get("TELEGRAM_USER_ID"))
FIREBASE_ENCODED = os.environ.get("FIREBASE_CREDENTIALS_ENCODED")

# Firebase setup
decoded = base64.b64decode(FIREBASE_ENCODED)
creds_dict = json.loads(decoded)
cred = credentials.Certificate(creds_dict)
firebase_app = initialize_app(cred, {
    'databaseURL': f'https://{creds_dict["project_id"]}.firebaseio.com'
})
db_root = db.reference("/")

# Celery config
CELERY_BROKER = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
celery = Celery(__name__, broker=CELERY_BROKER)
celery.conf.update(result_backend=CELERY_BROKER)

# Flask secret key
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-please")

# Telegram webhook route
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json()
        logger.info("Update received: %s", json.dumps(data))

        if "message" not in data:
            return jsonify({"ok": True})

        chat_id = data["message"]["chat"]["id"]
        user_id = data["message"]["from"]["id"]
        text = data["message"].get("text", "")

        if not is_valid_user(user_id):
            send_telegram_message(chat_id, "Access denied.")
            return jsonify({"ok": True})

        # Command handler
        response = handle_command(text, user_id=user_id)
        send_telegram_message(chat_id, response)

    except Exception as e:
        logger.exception("Error in webhook")
        send_telegram_message(USER_ID, f"Bot error: {e}")

    return jsonify({"ok": True})

# Health check
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

# Manually trigger bot task
@app.route("/start_bot", methods=["GET"])
def start_bot_route():
    run_auto_bot_task.delay()
    return jsonify({"status": "bot started"}), 200

# POST trigger
@app.route("/trigger", methods=["POST"])
def trigger_task():
    try:
        content = request.json or {}
        run_auto_bot_task.delay(content)
        return jsonify({"status": "manual trigger received"}), 202
    except Exception as e:
        logger.error("Trigger task error: %s", e)
        return jsonify({"error": str(e)}), 500

# Firebase write test
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
        logger.error("Firebase write failed: %s", e)
        return jsonify({"error": str(e)}), 500

# Firebase read test
@app.route("/test_read", methods=["GET"])
def test_read():
    try:
        result = db_root.child("test_node").get()
        return jsonify({"data": result}), 200
    except Exception as e:
        logger.error("Firebase read failed: %s", e)
        return jsonify({"error": str(e)}), 500

# Telegram send test
@app.route("/send_test", methods=["GET"])
def send_test_message():
    try:
        send_telegram_message(USER_ID, "Test message from /send_test endpoint.")
        return jsonify({"sent": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Celery task test
@app.route("/test_celery", methods=["GET"])
def test_celery():
    try:
        run_auto_bot_task.delay({"source": "manual_test"})
        return jsonify({"status": "celery triggered"}), 200
    except Exception as e:
        logger.error("Celery test error: %s", e)
        return jsonify({"error": str(e)}), 500

# AI Plugin manifest
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

# Serve OpenAPI spec
@app.route("/openapi.yaml", methods=["GET"])
def openapi_spec():
    try:
        return send_file("openapi.yaml")
    except Exception as e:
        logger.error("OpenAPI spec not found: %s", e)
        return jsonify({"error": "OpenAPI spec not found"}), 404

# Serve static files
@app.route("/static/<path:filename>", methods=["GET"])
def static_files(filename):
    try:
        return send_file(f"static/{filename}")
    except Exception as e:
        logger.error("Static file not found: %s", e)
        return jsonify({"error": "Static file not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=True)
