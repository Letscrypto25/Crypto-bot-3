from utils.logger_utils import get_logger
from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref
from encryption import decrypt_data
from exchanges import get_balance  # using our updated get_balance

logger = get_logger(__name__)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    try:
        # Fetch user data from Firebase using Telegram user ID
        user_data = firebase_ref.child(user_id).get()
        if not user_data:
            await update.message.reply_text("❌ You're not registered. Use /register first.")
            return

        # Determine exchange and get encrypted API keys
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

        # Decrypt the keys
        if not api_key_encrypted or not secret_encrypted:
            await update.message.reply_text(f"❌ Missing {exchange} API keys in your account.")
            return

        api_key = decrypt_data(api_key_encrypted)
        secret = decrypt_data(secret_encrypted)

        if not api_key or not secret:
            await update.message.reply_text("❌ Could not decrypt your API keys.")
            return

        # Prepare user credentials for get_balance
        user_credentials = {
            "luno_api_key": api_key,
            "luno_api_secret": secret,
            "binance_api_key": api_key,
            "binance_api_secret": secret
        }

        # Fetch balance using explicit user ID (Telegram ID) as `id`
        balances = await get_balance(
            id=user_id,
            source=exchange,
            user=user_credentials
        )

        if not balances:
            await update.message.reply_text("❌ Could not fetch your balance.")
            return

        # Format balance for display
        balance_msg = f"💰 *Your {exchange.capitalize()} Balance:*\n"
        for asset, balance in balances.items():
            balance_msg += f"• {asset.upper()}: `{balance}`\n"

        await update.message.reply_text(balance_msg, parse_mode="Markdown")

    except Exception as e:
        logger.exception("Error in balance_command")
        await update.message.reply_text(f"❌ An error occurred: {e}")
