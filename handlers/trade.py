# handlers/trade.py

from telegram import Update
from telegram.ext import ContextTypes
from database import get_user
from crypto.luno import place_luno_order
from crypto.binance import place_binance_order
from utils import decrypt_api_key, decrypt_api_secret

async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args

    if len(args) < 4:
        await update.message.reply_text("Usage: /trade <exchange> <buy/sell> <symbol> <amount> <password>")
        return

    exchange, side, symbol, amount_str, *rest = args
    password = rest[-1] if rest else None
    if not password:
        await update.message.reply_text("Password is required to confirm trade.")
        return

    user = get_user(user_id)
    if not user or not user.get("active"):
        await update.message.reply_text("You are not registered or active.")
        return

    # Validate password
    stored_pw = user.get("password")
    if not stored_pw or password != stored_pw:
        await update.message.reply_text("Incorrect password.")
        return

    try:
        amount = float(amount_str)
    except ValueError:
        await update.message.reply_text("Invalid amount format.")
        return

    try:
        api_key = decrypt_api_key(user["api_key"])
        api_secret = decrypt_api_secret(user["api_secret"])

        if exchange.lower() == "luno":
            result = place_luno_order(api_key, api_secret, side, symbol, amount)
        elif exchange.lower() == "binance":
            result = place_binance_order(api_key, api_secret, side, symbol, amount)
        else:
            await update.message.reply_text("Invalid exchange.")
            return

        await update.message.reply_text(f"Trade placed: {result}")
    except Exception as e:
        await update.message.reply_text(f"Trade failed: {e}")
