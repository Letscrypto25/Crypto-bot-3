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
        # Fetch user data from database
        user = get_user_data(user_id)
        if not user or "exchange" not in user:
            await update.message.reply_text("🚫 You're not registered. Use /register first.")
            return

        exchange = user["exchange"].lower()

        # Determine the correct API key and secret fields
        if exchange == "luno":
            api_key_encrypted = user.get("luno_api_key")
            secret_encrypted = user.get("luno_api_secret")
        elif exchange == "binance":
            api_key_encrypted = user.get("binance_api_key")
            secret_encrypted = user.get("binance_api_secret")
        else:
            await update.message.reply_text("❌ Unsupported exchange stored in your profile.")
            return

        # Decrypt API key and secret
        api_key = await decrypt_data(api_key_encrypted) if api_key_encrypted else None
        secret = await decrypt_data(secret_encrypted) if secret_encrypted else None

        if not api_key or not secret:
            await update.message.reply_text("⚠️ Your API credentials seem invalid or corrupted. Please /register again.")
            return

        logger.info(f"Fetching balance for user {user_id} on {exchange}")

        # Pass correct parameter names to get_balance
        if exchange == "luno":
            balances = await get_balance(
                luno_api_key=api_key,
                luno_api_secret=secret,
                source=exchange
            )
        elif exchange == "binance":
            balances = await get_balance(
                binance_api_key=api_key,
                binance_api_secret=secret,
                source=exchange
            )
        else:
            # Defensive fallback, should never be reached
            await update.message.reply_text("❌ Unknown exchange in your profile.")
            return

        if not balances:
            await update.message.reply_text("⚠️ Could not retrieve balance.")
            return

        # Build the balance message
        msg = "*💰 Your Balance:*\n"
        for coin, amount in balances.items():
            try:
                if float(amount) > 0:
                    msg += f"• `{coin}`: `{amount}`\n"
            except (ValueError, TypeError):
                continue  # Skip entries with non-numeric values

        if msg == "*💰 Your Balance:*\n":
            msg += "_No funds detected in your account._"

        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.exception("Error in balance_command")
        await update.message.reply_text("❌ An error occurred while fetching your balance.")
