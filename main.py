import logging
import os
import json
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app for health checks
flask_app = Flask(__name__)

@flask_app.route("/")
def health_check():
    return "OK", 200

# Webhook handler
@flask_app.route(f"/webhook/<token>", methods=["POST"])
def telegram_webhook(token):
    if token != os.getenv("BOT_TOKEN"):
        logger.error(f"Unauthorized access: Token mismatch. Expected {os.getenv('BOT_TOKEN')}, got {token}")
        return "Unauthorized", 403
    
    # Log the incoming request
    logger.info(f"Received webhook for token: {token}")
    
    # Process the incoming update asynchronously
    update = Update.de_json(request.json, application.bot)
    asyncio.ensure_future(application.process_update(update))  # Ensure task is created without breaking event loop
    
    return "OK", 200

# Telegram command handlers
async def start(update: Update, context):
    await update.message.reply_text("Hello, I am your crypto trading bot!")

async def help(update: Update, context):
    await update.message.reply_text("How can I assist you with your crypto trades?")

# Main bot setup
async def setup_bot():
    TOKEN = os.getenv("BOT_TOKEN")
    webhook_url = f"https://crypto-bot-3-white-wind-424.fly.dev/webhook/{TOKEN}"
    
    # Create the Telegram application instance
    global application
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers to the bot
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    
    # Set webhook URL
    await application.bot.set_webhook(webhook_url)

    # Run the webhook handler using Flask (with async capability)
    await application.run_webhook(
        listen="0.0.0.0",  # Ensure it listens on all network interfaces
        port=8080,         # Ensure it listens on port 8080
        url_path=f"webhook/{TOKEN}",
        webhook_url=webhook_url,
        web_app=flask_app,  # Embed Flask app within the application
    )

if __name__ == "__main__":
    asyncio.run(setup_bot())
