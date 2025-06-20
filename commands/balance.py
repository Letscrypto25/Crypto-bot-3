from utils.logger_utils import get_logger
from telegram import Update
from telegram.ext import ContextTypes
import asyncio
from database import firebase_ref
from encryption import decrypt_data
from exchanges import get_balance  # get_balance should now assume decrypted keys

logger = get_logger(__name__)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    try:
        # Fetch user data by their Telegram ID
        user_data = firebase_ref.child(user_id).get()
        if not user_data:
            await update.message.reply_text("❌ You're not registered. Use /register first.")
            return

        # Determine exchange
        exchange = user_data.get("exchange", "").lower()
        if exchange not in ("luno", "binance"):
            await update.message.reply_text("❌ Unknown exchange specified in your data.")
            return

        # Get encrypted keys from user data
        api_key_encrypted = (
            user_data.get(f"{exchange}_api_key")
            or user_data.get("api_key")
        )
        secret_encrypted = (
            user_data.get(f"{exchange}_api_secret")
            or user_data.get("api_secret")
        )

        if not api_key_encrypted or not secret_encrypted:
            await update.message.reply_text(f"❌ Missing {exchange} API keys in your account.")
            return

        # Decrypt keys
        api_key = decrypt_data(api_key_encrypted)
        secret = decrypt_data(secret_encrypted)

        if not api_key or not secret:
            await update.message.reply_text("❌ Could not decrypt your API keys.")
            return

        # Match the key names expected by get_balance()
        if exchange == "luno":
            decrypted_user_data = {
                "luno_api_key": api_key,
                "luno_api_secret": secret,
            }
        elif exchange == "binance":
            decrypted_user_data = {
                "binance_api_key": api_key,
                "binance_api_secret": secret,
            }
        else:
            await update.message.reply_text("❌ Unknown exchange. Cannot process.")
            return

        # Optional debug
        logger.info(f"[Balance] Decrypted user data: {decrypted_user_data}")

        # Run get_balance (now only works with decrypted input)
        loop = asyncio.get_running_loop()
        balances = await loop.run_in_executor(
            None,
            get_balance,
            user_id,
            exchange,
            decrypted_user_data
        )

        if not balances:
            await update.message.reply_text("❌ Could not fetch your balance.")
            return

        # Format the balance output
        balance_msg = f"💰 *Your {exchange.capitalize()} Balance:*\n"
        for asset, balance in balances.items():
            balance_msg += f"• {asset.upper()}: `{balance}`\n"

        await update.message.reply_text(balance_msg, parse_mode="Markdown")

    except Exception as e:
        logger.exception("Error in balance_command")
        await update.message.reply_text(f"❌ An error occurred: {e}")
