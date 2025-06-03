async def trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_data = get_user_data(user_id)

    if not user_data or 'exchange' not in user_data:
        await update.message.reply_text("You're not registered. Use /register first.")
        return

    try:
        # Parse args
        if len(context.args) < 3:
            await update.message.reply_text("Usage: /trade <BUY/SELL> <SYMBOL> <AMOUNT>")
            return

        action = context.args[0].upper()
        if action not in ("BUY", "SELL"):
            await update.message.reply_text("Invalid action. Use BUY or SELL.")
            return

        symbol = context.args[1].upper()
        amount = float(context.args[2])

        # Get price
        exchange = user_data.get("exchange")
        price = get_price(user_id=user_id, source=exchange, symbol=symbol)
        if not price:
            await update.message.reply_text("❌ Failed to fetch price.")
            return

        # Save trade
        trade_record = {
            "symbol": symbol,
            "amount": amount,
            "side": action,
            "price": price,
            "timestamp": datetime.utcnow().isoformat()
        }
        save_trade(user_id, trade_record)
        await update.message.reply_text(f"✅ {action} {amount} {symbol} at {price} — Executed")

    except Exception as e:
        logger.exception("Trade error")
        await update.message.reply_text(f"❌ Trade failed: {e}")
