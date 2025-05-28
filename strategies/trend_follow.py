def execute(user):
    """
    Trend Following Strategy:
    - Buy when MA20 > MA50 and price > MA20 (uptrend)
    - Sell when MA20 < MA50 and price < MA20 (downtrend)
    Logs profit/loss to Firebase and sends notifications.
    """
    from trading_api import get_moving_average, get_binance_price, trade_on_binance
    from notifications import notify_user_profit_loss
    from firebase_admin import db
    import time

    symbol = "BTC/USDT"
    user_id = user["user_id"]
    risk = user.get("risk_tolerance", 0.02)

    # Fetch data
    price = get_binance_price(user, symbol)
    ma_20 = get_moving_average(user, symbol, period=20)
    ma_50 = get_moving_average(user, symbol, period=50)

    if None in (price, ma_20, ma_50):
        print(f"[{user_id}] Could not fetch trend data.")
        return

    print(f"[{user_id}] Price: {price} | MA20: {ma_20} | MA50: {ma_50}")

    # Determine trend
    action = None
    if ma_20 > ma_50 and price > ma_20:
        action = "buy"
        print(f"[{user_id}] Uptrend — BUY")
    elif ma_20 < ma_50 and price < ma_20:
        action = "sell"
        print(f"[{user_id}] Downtrend — SELL")
    else:
        print(f"[{user_id}] No clear trend — HOLD")
        return

    # Execute trade
    profit_or_loss = trade_on_binance(user, action=action, symbol=symbol, amount=risk)

    # Log to Firebase
    try:
        trades_ref = db.reference(f"/users/{user_id}/trades")
        trades_ref.push({
            "timestamp": int(time.time()),
            "strategy": "trend_following",
            "action": action,
            "profit_or_loss": profit_or_loss,
        })
    except Exception as e:
        print(f"[{user_id}] Error logging trade to Firebase: {e}")

    # Notify user
    notify_user_profit_loss(user_id, action, profit_or_loss)
