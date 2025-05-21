def execute(user):
    """
    RSI Strategy:
    Buy when RSI < oversold threshold,
    Sell when RSI > overbought threshold.
    Logs profit/loss to Firebase and sends notifications.
    """
    from trading_api import get_rsi, trade_on_binance
    from notifications import notify_user_profit_loss
    from firebase_admin import db
    import time

    symbol = "BTC/USDT"
    period = user.get("rsi_period", 14)
    oversold = user.get("rsi_oversold", 30)
    overbought = user.get("rsi_overbought", 70)
    risk = user.get("risk_tolerance", 0.02)
    user_id = user["user_id"]

    rsi = get_rsi(user, symbol, period)

    if rsi is None:
        print(f"[{user_id}] Could not fetch RSI.")
        return

    print(f"[{user_id}] RSI({period}): {rsi}")

    action = None
    if rsi < oversold:
        action = "buy"
        print(f"[{user_id}] RSI below {oversold} — BUY signal")
    elif rsi > overbought:
        action = "sell"
        print(f"[{user_id}] RSI above {overbought} — SELL signal")
    else:
        print(f"[{user_id}] RSI neutral — HOLD")
        return

    # Execute trade
    profit_or_loss = trade_on_binance(user, action=action, symbol=symbol, amount=risk)

    # Log profit/loss to Firebase with timestamp
    try:
        trades_ref = db.reference(f"/users/{user_id}/trades")
        trades_ref.push({
            "timestamp": int(time.time()),
            "strategy": "rsi",
            "action": action,
            "profit_or_loss": profit_or_loss,
        })
    except Exception as e:
        print(f"[{user_id}] Error logging trade to Firebase: {e}")

    # Send notification with trade result
    notify_user_profit_loss(user_id, action, profit_or_loss)
