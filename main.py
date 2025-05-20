import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters
)
from firebase_admin import credentials, initialize_app

import commands  # Your commands.py module
from database import initialize_firebase

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Firebase before starting the bot
def setup_firebase():
    # Use your Firebase service account key JSON path
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "path/to/serviceAccountKey.json")
    try:
        cred = credentials.Certificate(cred_path)
        initialize_app(cred)
        initialize_firebase()  # Your custom database.py setup if needed
        logger.info("Firebase initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        raise e


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sorry, I didn't understand that command. Use /help to see available commands.")


def main():
    # Load Telegram token from env variable or replace here
    token = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")

    setup_firebase()

    # Create bot application
    app = ApplicationBuilder().token(token).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", commands.start))
    app.add_handler(CommandHandler("help", commands.help_command))
    app.add_handler(CommandHandler("register", commands.register))
    app.add_handler(CommandHandler("balance", commands.balance))
    app.add_handler(CommandHandler("trade", commands.trade))
    app.add_handler(CommandHandler("autobot", commands.autobot))
    app.add_handler(CommandHandler("autobot_config", commands.autobot_config))
    app.add_handler(CommandHandler("leaderboard", commands.get_leaderboard))
    app.add_handler(CommandHandler("setplatform", commands.set_platform))
    app.add_handler(CommandHandler("setstrategy", commands.set_strategy))
    app.add_handler(CommandHandler("setamount", commands.set_amount))
    app.add_handler(CommandHandler("showconfig", commands.show_config))
    app.add_handler(CommandHandler("setbase", commands.set_base))
    app.add_handler(CommandHandler("stopautobot", commands.stop_autobot))

    # Unknown command handler
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("Bot started polling...")
    app.run_polling()

    main()if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=True)
