import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Your Telegram user ID (replace with your own ID)
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

# Start command
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Welcome! Bot is active and ready.")

# Error handler
def error_handler(update: object, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # Send the error to your Telegram account
    if ADMIN_CHAT_ID:
        try:
            context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"⚠️ Bot Error:\n{context.error}"
            )
        except Exception as e:
            logger.error(f"Failed to send error to admin: {e}")

# Main function
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN not set in environment variables")

    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
