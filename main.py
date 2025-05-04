import logging
import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import firebase_admin
from firebase_admin import credentials

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firebase using secret loaded from environment variable
firebase_credentials_json = os.getenv("FIREBASE_CREDENTIALS")
cred_dict = json.loads(firebase_credentials_json)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello, I am your crypto trading bot!")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("How can I assist you with your crypto trades?")

async def get_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Your current balance is: R1000")

async def check_trends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Current crypto trends: Bitcoin is trending upward.")

# Main bot function
async def main() -> None:
    TOKEN = "7874445351:AAEinr4HOv_zEj6rHbgzNZwbij0IdN9M7Ik"
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("get_balance", get_balance))
    application.add_handler(CommandHandler("check_trends", check_trends))

    # Set up Fly.io public webhook URL
    webhook_url = f"https://crypto-bot-3-white-wind-424.fly.dev/webhook/{TOKEN}"

    # Set Telegram webhook
    await application.bot.set_webhook(webhook_url)

    # Run bot listener on Fly-required port
    await application.run_webhook(
        listen="0.0.0.0",
        port=8080,
        url_path=f"webhook/{TOKEN}",
        webhook_url=webhook_url,
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
