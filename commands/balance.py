from utils.logger_utils import get_logger
from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref
from encryption import decrypt_data
from exchanges import get_balance  # Assuming you have this function to fetch balance

logger = get_logger(__name__)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    try:
        # Fetch user data from Firebase
        user_data = firebase_ref.child(user_id).get()
        if not user_data or 'exchange' not in user_data:
            await update.message.reply_text("❌ You're not registered. Use /register first.")
            return

        exchange = user_data.get("exchange")

        # Decrypt the API keys
        if exchange.lower() == "luno":
            api_key_encrypted = user_data.get("luno_api_key")
            secret_encrypted = user_data.get("luno_api_secret")
        elif exchange.lower() == "binance":
            api_key_encrypted = user_data.get("binance_api_key")
            secret_encrypted = user_data.get("binance_api_secret")
        else:
            await update.message.reply_text("❌ Unknown exchange specified.")
            return

        api_key = decrypt_data(api_key_encrypted) if api_key_encrypted else None
        secret = decrypt_data(secret_encrypted) if secret_encrypted else None

        if not api_key or not secret:
            await update.message.reply_text("❌ API keys not found or incomplete for your exchange.")
            return

        # Fetch balance
        balances = await get_balance(
            source=exchange,
            api_key=api_key,
            secret=secret
        )

        if not balances:
            await update.message.reply_text("❌ Could not fetch your balance.")
            return

        # Format balance nicely
        balance_msg = "💰 *Your Balance:*\n"
        for asset, balance in balances.items():
            balance_msg += f"• {asset.upper()}: `{balance}`\n"

        await update.message.reply_text(balance_msg, parse_mode="Markdown")

    except Exception as e:
        logger.exception("Error in balance_command")
        await update.message.reply_text(f"❌ An error occurred: {e}")
