
import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database import get_user_data
from encryption import decrypt_data
from exchanges import get_balance

logger = logging.getLogger(__name__)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    try:
        # This is a sync function; no await
        user = get_user_data(user_id)

        if not user or "exchange" not in user:
            await update.message.reply_text("🚫 You're not registered. Use /register first.")
            return

        exchange = user["exchange"].lower()

        if exchange == "luno":
            api_key_encrypted = user.get("luno_api_key")
            secret_encrypted = user.get("luno_api_secret")
        elif exchange == "binance":
            api_key_encrypted = user.get("binance_api_key")
            secret_encrypted = user.get("binance_api_secret")
        else:
            await update.message.reply_text("❌ Unsupported exchange stored in your profile.")
            return

        # Decrypt only if keys exist, await decryption
        api_key = await decrypt_data(api_key_encrypted) if api_key_encrypted else None
        secret = await decrypt_data(secret_encrypted) if secret_encrypted else None

        if not api_key or not secret:
            await update.message.reply_text("⚠️ Your API credentials seem invalid or corrupted. Please /register again.")
            return

        logger.info(f"Fetching balance for user {user_id} on {exchange}")

        balances = await get_balance(api_key=api_key, secret=secret, source=exchange)

        if not balances:
            await update.message.reply_text("⚠️ Could not retrieve balance.")
            return

        msg = "*💰 Your Balance:*\n"
        for coin, amount in balances.items():
            try:
                if float(amount) > 0:
                    msg += f"• `{coin}`: `{amount}`\n"
            except (ValueError, TypeError):
                continue  # Skip if amount can't be parsed to float

        if msg == "*💰 Your Balance:*\n":
            msg += "_No funds detected in your account._"

        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    except Exception:
        logger.exception("Error in balance_command")
        await update.message.reply_text("❌ An error occurred while fetching your balance.")
