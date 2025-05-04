import logging
import os
import json
import asyncio
from quart import Quart, request
from telegram import Update
from telegram.ext import Application, CommandHandler

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Quart app for health checks and webhook handling
flask_app = Quart(__name__)

@flask_app.route("/")
async def health_check():
    return "OK", 200

# Webhook handler
@flask_app.route(f"/webhook/<token>", methods=["POST"])
async def telegram_webhook(token):
    if token != os.getenv("BOT_TOKEN"):
        logger.error(f"Unauthorized access: Token mismatch. Expected {os.getenv('BOT_TOKEN')}, got {token}")
        return "Unauthorized", 403
    
    # Log the incoming request
    logger.info(f"Received webhook for token: {token}")
    
    # Process the incoming update asynchronously
    update = Update.de_json(await request.json(), application.bot)
    await application.process_update(update)  # Ensure task is created properly with await
    
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

    # Run the Quart app to handle webhook asynchronously
    await flask_app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    asyncio.run(setup_bot())
