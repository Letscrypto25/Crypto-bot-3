import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
from flask import Flask
import firebase_admin
from firebase_admin import credentials

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask for webhook
app = Flask(__name__)

# Initialize Firebase from file path directly (Termux home)
firebase_credentials_path = "/data/data/com.termux/files/home/firebase.json"
cred = credentials.Certificate(firebase_credentials_path)
firebase_admin.initialize_app(cred)

# Define your command functions
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hello, I am your crypto trading bot!')

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('How can I assist you with your crypto trades?')

async def get_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Placeholder for fetching balance (add actual logic here)
    await update.message.reply_text("Your current balance is: R1000")

async def check_trends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Placeholder for checking trends (add actual logic here)
    await update.message.reply_text("Current crypto trends: Bitcoin is trending upward.")

# Main function to set up the bot
async def main() -> None:
    """Start the bot."""
    # Initialize the application with your bot's token
    application = Application.builder().token("7874445351:AAEinr4HOv_zEj6rHbgzNZwbij0IdN9M7Ik").build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("get_balance", get_balance))
    application.add_handler(CommandHandler("check_trends", check_trends))

    # Set up webhook
    webhook_url = "https://your-fly-app-url.com/webhook/7874445351:AAEinr4HOv_zEj6rHbgzNZwbij0IdN9M7Ik"

    # Set webhook
    await application.bot.set_webhook(webhook_url)

    # Start the webhook listener
    await application.run_webhook(
        listen="0.0.0.0",
        port=8080,
        url_path="webhook/7874445351:AAEinr4HOv_zEj6rHbgzNZwbij0IdN9M7Ik",
        webhook_url=webhook_url,
        keyfile=None,
        certfile=None,
    )

# Flask route for handling webhook requests
@app.route(f"/webhook/<string:token>", methods=["POST"])
def webhook(token):
    if token != "7874445351:AAEinr4HOv_zEj6rHbgzNZwbij0IdN9M7Ik":
        return "Unauthorized", 403
    return "OK", 200

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
    # app.run(host='0.0.0.0', port=8080)
