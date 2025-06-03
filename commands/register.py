import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref
from encryption import encrypt_data

logger = logging.getLogger(__name__)

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args

    # Validate the input arguments
    if len(args) != 3:
        await update.message.reply_text("Usage: /register <exchange> <api_key> <secret>")
        return

    exchange, api_key, secret = args
    exchange = exchange.lower()

    if exchange not in ("luno", "binance"):
        await update.message.reply_text("❌ Unsupported exchange. Use 'luno' or 'binance'.")
        return

    try:
        # Encrypt the sensitive API credentials
        encrypted_api_key = encrypt_data(api_key)
        encrypted_secret = encrypt_data(secret)

        # Prepare the data to store in Firebase
        updates = {
            "exchange": exchange
        }
        if exchange == "luno":
            updates["luno_api_key"] = encrypted_api_key
            updates["luno_api_secret"] = encrypted_secret
        else:  # binance
            updates["binance_api_key"] = encrypted_api_key
            updates["binance_api_secret"] = encrypted_secret

        # Save the data in the Firebase database
        firebase_ref.child(user_id).update(updates)

        await update.message.reply_text("✅ Registered successfully with your exchange details.")

    except Exception as e:
        logger.exception("Error during registration")
        await update.message.reply_text("❌ An error occurred during registration.")
