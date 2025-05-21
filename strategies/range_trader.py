def execute(user):
    """
    Range Trading Strategy:
    Buy when price drops below lower bound, sell when price rises above upper bound.
    """
    from trading_api import get_binance_price, trade_on_binance

    symbol = "BTC/USDT"
    price = get_binance_price(user, symbol)

    if not price:
        print(f"[{user['user_id']}] Could not fetch price.")
        return

    # Pull range from user settings or use default values
    lower_bound = user.get("range_lower_bound", 29500)
    upper_bound = user.get("range_upper_bound", 30500)
    risk = user.get("risk_tolerance", 0.02)  # 2% default capital

    print(f"[{user['user_id']}] Price: {price} | Range: {lower_bound} - {upper_bound}")

    if price < lower_bound:
        print(f"[{user['user_id']}] Price below range — BUY")
        trade_on_binance(user, action="buy", symbol=symbol, amount=risk)

    elif price > upper_bound:
        print(f"[{user['user_id']}] Price above range — SELL")
        trade_on_binance(user, action="sell", symbol=symbol, amount=risk)

    else:
        print(f"[{user['user_id']}] Price within range — HOLD")
