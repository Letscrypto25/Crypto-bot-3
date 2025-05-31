import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database import get_user_data
from encryption import decrypt_data
from exchanges import get_balance

logger = logging.getLogger(__name__)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    try:
        user = get_user_data(user_id)
        if not user or "exchange" not in user:
            await update.message.reply_text("You're not registered. Use /register first.")
            return

        # Decrypt the sensitive data and temporarily inject them into Firebase for backward-compatible get_balance
        decrypted_user = {
            "exchange": user["exchange"],
            "api_key": decrypt_data(user["api_key"]),
            "secret": decrypt_data(user["secret"]),
        }

        # Call get_balance as if it fetches its own data
        balances = get_balance(user_id=user_id, source=decrypted_user["exchange"])
        if not balances:
            await update.message.reply_text("Could not retrieve balance.")
            return

        msg = "*Your Balance:*\n"
        for coin, amount in balances.items():
            if float(amount) > 0:
                msg += f"{coin}: {amount}\n"

        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.exception("balance error")
        await update.message.reply_text("An error occurred while fetching your balance.")
