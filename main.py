import os
import json
import logging
import base64
from flask import Flask, request, jsonify
from firebase_admin import credentials, initialize_app, db
from utils import get_env, send_telegram_message, is_valid_user
from tasks import run_auto_bot_task
from celery import Celery

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Telegram secrets
BOT_TOKEN = get_env("TELEGRAM_BOT_TOKEN")
USER_ID = int(get_env("TELEGRAM_USER_ID"))

# Firebase setup
encoded_creds = get_env("FIREBASE_CREDENTIALS_ENCODED")
decoded = base64.b64decode(encoded_creds)
creds_dict = json.loads(decoded)
cred = credentials.Certificate(creds_dict)
firebase_app = initialize_app(cred, {
    'databaseURL': 'https://{}.firebaseio.com'.format(creds_dict['project_id'])
})
db_root = db.reference("/")

# Celery config
CELERY_BROKER = get_env("REDIS_URL", "redis://localhost:6379/0")
celery = Celery(__name__, broker=CELERY_BROKER)
celery.conf.update(result_backend=CELERY_BROKER)

# Flask secret
app.secret_key = get_env("FLASK_SECRET_KEY", "change-this-please")

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

        # Handle user command
        response = handle_command(text, user_id=user_id)
        send_telegram_message(chat_id, response)

    except Exception as e:
        logger.exception("Error in webhook")
        send_telegram_message(USER_ID, f"Bot error: {e}")

    return jsonify({"ok": True})
    
# Health check route
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

# Trigger the auto bot manually from a Telegram command
@app.route("/start_bot", methods=["GET"])
def start_bot_route():
    run_auto_bot_task.delay()
    return jsonify({"status": "bot started"}), 200

# Manual trigger via POST (optionally with payload)
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

# Deployment hint
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
    
# Load OpenAPI spec file for plugin (if exists)
@app.route("/openapi.yaml", methods=["GET"])
def openapi_spec():
    try:
        return send_file("openapi.yaml")
    except Exception as e:
        logger.error("OpenAPI spec not found: %s", e)
        return jsonify({"error": "OpenAPI spec not found"}), 404

# Serve static files (like logo)
@app.route("/static/<path:filename>", methods=["GET"])
def static_files(filename):
    try:
        return send_file(f"static/{filename}")
    except Exception as e:
        logger.error("Static file not found: %s", e)
        return jsonify({"error": "Static file not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
