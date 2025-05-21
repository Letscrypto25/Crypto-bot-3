def execute(user):
    """
    Mean Reversion Strategy:
    If current price deviates significantly from recent average, expect it to return (revert) to the mean.
    """
    from trading_api import get_price_history, trade_on_binance

    symbol = "BTC/USDT"
    interval = "1m"
    lookback = 10  # candles for moving average

    risk = user.get("risk_tolerance", 0.02)
    profit_target = user.get("profit_target", 50)

    prices = get_price_history(user, symbol, interval, lookback)

    if not prices or len(prices) < lookback:
        print(f"[{user['user_id']}] Not enough price data.")
        return

    current_price = prices[-1]
    average_price = sum(prices) / len(prices)
    deviation = current_price - average_price

    print(f"[{user['user_id']}] Current: {current_price}, Average: {average_price}")

    # Define a trigger threshold for deviation
    trigger = 0.01 * average_price  # 1% of mean price

    if deviation > trigger:
        print(f"[{user['user_id']}] Price above mean - SELL")
        trade_on_binance(user, action="sell", symbol=symbol, amount=risk)

    elif deviation < -trigger:
        print(f"[{user['user_id']}] Price below mean - BUY")
        trade_on_binance(user, action="buy", symbol=symbol, amount=risk)

    else:
        print(f"[{user['user_id']}] Price near mean - no action")
