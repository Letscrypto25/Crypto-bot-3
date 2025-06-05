from utils.logger_utils import get_logger
from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref
from encryption import encrypt_data

logger_utils = getLogger(__name__)

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args

    # Validate input arguments
    if len(args) != 3:
        await update.message.reply_text("Usage: /register <Luno or  Binance> <api_key> <secret>")
        return

    exchange, api_key, secret = args
    exchange = exchange.lower()

    if exchange not in ("luno", "binance"):
        await update.message.reply_text("❌ Unsupported exchange. Use 'luno' or 'binance'.")
        return

    try:
        # Encrypt API credentials
        encrypted_api_key = encrypt_data(api_key)
        encrypted_secret = encrypt_data(secret)

        # Prepare user data
        updates = {
            "exchange": exchange,
            f"{exchange}_api_key": encrypted_api_key,
            f"{exchange}_api_secret": encrypted_secret
        }

        # Update Firebase
        firebase_ref.child(user_id).update(updates)

        await update.message.reply_text(
            f"✅ Successfully registered {exchange.capitalize()} exchange details!"
        )
        logger.info(f"User {user_id} registered with {exchange.capitalize()}")

    except Exception as e:
        logger.exception("Error during registration")
        await update.message.reply_text(f"❌ An error occurred during registration: {e}")
