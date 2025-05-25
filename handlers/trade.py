# handlers/trade.py

from telegram import Update
from telegram.ext import ContextTypes
from trading.core import execute_trade
from database import firebase_ref

async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args

    if len(args) < 3:
        await update.message.reply_text("Usage: /trade <coin> <amount> <buy/sell>")
        return

    coin, amount, side = args[0].upper(), args[1], args[2].lower()

    user_data = firebase_ref.child(user_id).get()
    if not user_data:
        await update.message.reply_text("You are not registered. Use /register first.")
        return

    api_key = user_data.get("api_key")
    api_secret = user_data.get("api_secret")
    exchange = user_data.get("exchange")

    if not api_key or not api_secret:
        await update.message.reply_text("Incomplete API credentials.")
        return

    result = execute_trade(exchange, api_key, api_secret, coin, amount, side)

    if result.get("success"):
        await update.message.reply_text(f"{side.capitalize()} order placed for {amount} {coin}.")
    else:
        await update.message.reply_text(f"Trade failed: {result.get('error', 'Unknown error')}")
