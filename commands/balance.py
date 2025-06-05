from utils.logger_utils import get_logger
from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref
from encryption import decrypt_data
from exchanges import get_balance  # This must accept explicit api_key/secret

logger = get_logger(__name__)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    try:
        # Fetch user data by their Telegram ID
        user_data = firebase_ref.child(user_id).get()
        if not user_data:
            await update.message.reply_text("❌ You're not registered. Use /register first.")
            return

        # Check exchange and get encrypted keys
        exchange = user_data.get("exchange", "").lower()
        if exchange == "luno":
            api_key_encrypted = user_data.get("luno_api_key")
            secret_encrypted = user_data.get("luno_api_secret")
        elif exchange == "binance":
            api_key_encrypted = user_data.get("binance_api_key")
            secret_encrypted = user_data.get("binance_api_secret")
        else:
            await update.message.reply_text("❌ Unknown exchange specified in your data.")
            return

        # Decrypt the keys explicitly
        if not api_key_encrypted or not secret_encrypted:
            await update.message.reply_text(f"❌ Missing {exchange} API keys in your account.")
            return

        api_key = decrypt_data(api_key_encrypted)
        secret = decrypt_data(secret_encrypted)

        if not api_key or not secret:
            await update.message.reply_text("❌ Could not decrypt your API keys.")
            return

        # Fetch balance using explicit keys
        balances = await get_balance(
            source=exchange,
            api_key=api_key,
            secret=secret
        )

        if not balances:
            await update.message.reply_text("❌ Could not fetch your balance.")
            return

        # Format balance nicely
        balance_msg = f"💰 *Your {exchange.capitalize()} Balance:*\n"
        for asset, balance in balances.items():
            balance_msg += f"• {asset.upper()}: `{balance}`\n"

        await update.message.reply_text(balance_msg, parse_mode="Markdown")

    except Exception as e:
        logger.exception("Error in balance_command")
        await update.message.reply_text(f"❌ An error occurred: {e}")
