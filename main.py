import os
import logging
from flask import Flask, request
import telegram

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Retrieve environment variables
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')  # Set this to your Fly.io app URL + /token

if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN is not set.")
    raise ValueError("TELEGRAM_TOKEN is required")

bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Define the webhook endpoint
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    try:
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        if update.message:  # Ensure message exists
            chat_id = update.message.chat.id
            message = update.message.text
            bot.send_message(chat_id=chat_id, text="Echo: " + message)
        return "ok"
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return "Error occurred", 500

# Simple health check route
@app.route("/")
def index():
    return "Bot is running."

# Set webhook on first request
@app.before_first_request
def set_webhook():
    try:
        if WEBHOOK_URL:
            full_webhook_url = f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
            bot.set_webhook(url=full_webhook_url)
            logger.info(f"Webhook set to: {full_webhook_url}")
        else:
            logger.warning("WEBHOOK_URL not set.")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        raise

# Main entry point for the app
if __name__ == "__main__":
    try:
        app.run(port=int(os.environ.get("PORT", 8080)), host="0.0.0.0")
    except Exception as e:
        logger.error(f"Error starting the app: {e}")
        raise
