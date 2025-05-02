import os
import logging
from flask import Flask, request
import telegram

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Retrieve environment variables with proper checks
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')  # Set this to your Fly.io app URL + /token

if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN is not set. Please provide it as an environment variable.")
    raise ValueError("TELEGRAM_TOKEN is required")

if not WEBHOOK_URL:
    logger.error("WEBHOOK_URL is not set. Please provide it as an environment variable.")
    raise ValueError("WEBHOOK_URL is required")

# Initialize the Telegram Bot
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Define the webhook endpoint
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    try:
        # Parse the update from the Telegram API
        update = telegram.Update.de_json(request.get_json(force=True), bot)

        # Check if there's a message and process it
        if update.message:
            chat_id = update.message.chat.id
            message = update.message.text
            bot.send_message(chat_id=chat_id, text=f"Echo: {message}")
            logger.info(f"Received message: {message}")
        return "ok"
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return "Error occurred while processing the webhook", 500

# Simple health check route
@app.route("/")
def index():
    return "Bot is running."

# Set webhook on first request to ensure it is set only once
@app.before_first_request
def set_webhook():
    try:
        # Ensure that the webhook URL is provided and properly formed
        full_webhook_url = f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
        bot.set_webhook(url=full_webhook_url)
        logger.info(f"Webhook set to: {full_webhook_url}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        raise

# Main entry point for the app
if __name__ == "__main__":
    try:
        # Run Flask app, catching any errors in starting the server
        port = int(os.environ.get("PORT", 8080))  # Use port from environment, default to 8080
        app.run(port=port, host="0.0.0.0")
    except Exception as e:
        logger.error(f"Error starting the app: {e}")
        raise
