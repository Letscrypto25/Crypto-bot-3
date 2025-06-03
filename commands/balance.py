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
        user = await get_user_data(user_id)  # Await if async

        if not user or "exchange" not in user:
            await update.message.reply_text("🚫 You're not registered. Use /register first.")
            return

        exchange = user["exchange"]

        if exchange == "luno":
            api_key_encrypted = user.get("luno_api_key")
            secret_encrypted = user.get("luno_api_secret")
        elif exchange == "binance":
            api_key_encrypted = user.get("binance_api_key")
            secret_encrypted = user.get("binance_api_secret")
        else:
            await update.message.reply_text("❌ Unsupported exchange stored in your profile.")
            return

        api_key = safe_decrypt(api_key_encrypted)
        secret = safe_decrypt(secret_encrypted)

        if not api_key or not secret:
            await update.message.reply_text("⚠️ Your API credentials seem invalid or corrupted. Please /register again.")
            return

        logger.info(f"Fetching balance for user: {user_id} on {exchange}")

        balances = await get_balance(api_key=api_key, secret=secret, source=exchange)  # Await and pass keys

        if not balances:
            await update.message.reply_text("⚠️ Could not retrieve balance.")
            return

        msg = "*💰 Your Balance:*\n"
        for coin, amount in balances.items():
            if float(amount) > 0:
                msg += f"• `{coin}`: `{amount}`\n"

        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.exception("balance error")
        await update.message.reply_text("❌ An error occurred while fetching your balance.")
