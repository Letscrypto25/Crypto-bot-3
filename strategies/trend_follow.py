def execute(user):
    """
    Trend Following Strategy:
    - Buy when MA20 > MA50 and price > MA20 (uptrend)
    - Sell when MA20 < MA50 and price < MA20 (downtrend)
    """
    from trading_api import get_moving_average, get_binance_price, trade_on_binance

    symbol = "BTC/USDT"
    price = get_binance_price(user, symbol)
    ma_20 = get_moving_average(user, symbol, period=20)
    ma_50 = get_moving_average(user, symbol, period=50)

    if None in (price, ma_20, ma_50):
        print(f"[{user['user_id']}] Could not fetch trend data.")
        return

    print(f"[{user['user_id']}] Price: {price} | MA20: {ma_20} | MA50: {ma_50}")

    risk = user.get("risk_tolerance", 0.02)  # Default to 2% of capital

    if ma_20 > ma_50 and price > ma_20:
        print(f"[{user['user_id']}] Uptrend — BUY")
        trade_on_binance(user, action="buy", symbol=symbol, amount=risk)

    elif ma_20 < ma_50 and price < ma_20:
        print(f"[{user['user_id']}] Downtrend — SELL")
        trade_on_binance(user, action="sell", symbol=symbol, amount=risk)

    else:
        print(f"[{user['user_id']}] No clear trend — HOLD")
