import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from database import get_user_data, save_trade
from exchanges import get_price

logger = logging.getLogger(__name__)

async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_data = get_user_data(user_id)

    if not user_data or 'exchange' not in user_data:
        await update.message.reply_text("You're not registered. Use /register first.")
        return

    try:
        action = context.args[0].upper()
        symbol = context.args[1].upper()
        amount = float(context.args[2])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /trade <BUY/SELL> <SYMBOL> <AMOUNT>")
        return

    try:
        exchange = user_data.get("exchange")
        price = get_price(user_id=user_id, source=exchange, symbol=symbol)

        if not price:
            await update.message.reply_text("Failed to fetch price.")
            return

        trade_record = {
            "symbol": symbol,
            "amount": amount,
            "side": action,
            "price": price,
            "timestamp": datetime.utcnow().isoformat()
        }
        save_trade(user_id, trade_record)
        await update.message.reply_text(f"{action} {amount} {symbol} at {price} — Executed")

    except Exception as e:
        logger.exception("Trade error")
        await update.message.reply_text(f"Trade failed: {e}")
