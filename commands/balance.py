import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database import get_user_data
from encryption import decrypt_data
from exchanges import (
    get_binance_client,
    get_binance_price,
    get_luno_auth_header,
    get_luno_price,
    get_price,
    get_balance
)

logger = logging.getLogger(__name__)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    try:
        user = get_user_data(user_id)
        if not user or "exchange" not in user:
            await update.message.reply_text("You're not registered. Use /register first.")
            return

        # Decrypt the sensitive data before using
        user["api_key"] = decrypt_data(user["api_key"])
        user["secret"] = decrypt_data(user["secret"])

        balances = get_balance(user_id=user_id, source=user["exchange"], user_data=user)
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
