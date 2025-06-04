import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from database import get_user_data, save_trade
from price_feed import get_price  # Example; adjust import to your project
# from trades import execute_trade  # If you have actual trade logic!

logger = logging.getLogger(__name__)

async def trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    try:
        # Check user registration
        user_data = get_user_data(user_id)
        if not user_data or "exchange" not in user_data:
            await update.message.reply_text("🚫 You're not registered. Use /register first.")
            return

        # Validate args
        if len(context.args) < 3:
            await update.message.reply_text("Usage: /trade <BUY/SELL> <SYMBOL> <AMOUNT>")
            return

        action = context.args[0].upper()
        if action not in ("BUY", "SELL"):
            await update.message.reply_text("Invalid action. Use BUY or SELL.")
            return

        symbol = context.args[1].upper()
        try:
            amount = float(context.args[2])
        except ValueError:
            await update.message.reply_text("❌ Amount must be a number.")
            return

        # Get price
        exchange = user_data.get("exchange")
        price = await get_price(user_id=user_id, source=exchange, symbol=symbol)
        if not price:
            await update.message.reply_text("❌ Failed to fetch price.")
            return

        # Save trade record
        trade_record = {
            "symbol": symbol,
            "amount": amount,
            "side": action,
            "price": price,
            "timestamp": datetime.utcnow().isoformat()
        }
        await save_trade(user_id, trade_record)

        # Respond to user
        await update.message.reply_text(
            f"✅ {action} {amount} {symbol} at {price} — Executed!"
        )

    except Exception as e:
        logger.exception("Error in trade_command")
        await update.message.reply_text(f"❌ Trade failed: {e}")
