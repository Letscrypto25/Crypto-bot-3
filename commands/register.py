import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref
from encryption import ( 
    encrypt_data,
    decrypt_data,
    hash_password,
    verify_password
)

logger = logging.getLogger(__name__)

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    try:
        if len(context.args) != 3:
            await update.message.reply_text("Usage: /register <exchange> <api_key> <secret>")
            return

        exchange, api_key, secret = context.args
        exchange = exchange.lower()

        # Encrypt sensitive data before storing
        encrypted_api_key = encrypt_data(api_key)
        encrypted_secret = encrypt_data(secret)

        # Prepare exchange-specific field names
        if exchange == "luno":
            updates = {
                "exchange": exchange,
                "luno_api_key": encrypted_api_key,
                "luno_api_secret": encrypted_secret
            }
        elif exchange == "binance":
            updates = {
                "exchange": exchange,
                "binance_api_key": encrypted_api_key,
                "binance_api_secret": encrypted_secret
            }
        else:
            await update.message.reply_text("❌ Unsupported exchange. Use 'luno' or 'binance'.")
            return

        firebase_ref.child(user_id).update(updates)
        await update.message.reply_text("✅ Registered successfully with your exchange details.")

    except Exception as e:
        logger.exception("register error")
        await update.message.reply_text("❌ An error occurred during registration.")
