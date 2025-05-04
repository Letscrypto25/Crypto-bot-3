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

# Load Firebase credentials from environment variable
cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS"))
firebase_admin.initialize_app(cred)

# Define your command functions
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hello, I am your crypto trading bot!')

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('How can I assist you with your crypto trades?')

async def get_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Placeholder for fetching balance (add actual logic here)
    await update.message.reply_text("Your current balance is: R1000")  # Changed to Rand (ZAR)

async def check_trends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Placeholder for checking trends (add actual logic here)
    await update.message.reply_text("Current crypto trends: Bitcoin is trending upward.")

# Main function to set up the bot
async def main() -> None:
    """Start the bot."""
    # Fetch bot token from environment variable
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("Bot token not found in environment variables.")
        return

    # Initialize the application with your bot's token
    application = Application.builder().token(bot_token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("get_balance", get_balance))
    application.add_handler(CommandHandler("check_trends", check_trends))

    # Set up webhook
    webhook_url = f"https://your-fly-app-url.com/webhook/{bot_token}"

    # Set webhook
    await application.bot.set_webhook(webhook_url)
    
    # Start the webhook listener
    await application.run_webhook(
        listen="0.0.0.0",  # Listen on all interfaces
        port=8080,  # Changed port to 8080
        url_path=f"webhook/{bot_token}",  # Set the correct URL path for your webhook
        webhook_url=webhook_url,  # Provide the full URL for the webhook
        keyfile=None,  # Optionally add SSL keyfile if needed
        certfile=None,  # Optionally add SSL certificate if needed
    )

# Flask route for handling webhook requests
@app.route(f"/webhook/<string:token>", methods=["POST"])
def webhook(token):
    if token != os.getenv("BOT_TOKEN"):
        return "Unauthorized", 403

    # Handle the webhook data here if needed (logging, processing, etc.)
    return "OK", 200

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

    # Run Flask app on port 8080
    app.run(host='0.0.0.0', port=8080)
