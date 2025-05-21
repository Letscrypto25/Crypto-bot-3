def execute(user):
    """
    Momentum strategy that looks at short-term price trends.
    If price has been increasing steadily, we buy. If decreasing, we sell.
    """
    from trading_api import get_price_history, trade_on_binance

    symbol = "BTC/USDT"
    interval = "1m"  # 1-minute candles
    lookback = 5     # how many candles to check

    risk = user.get("risk_tolerance", 0.02)      # default 2%
    profit_target = user.get("profit_target", 50)  # default $50

    price_history = get_price_history(user, symbol, interval, lookback)

    if not price_history or len(price_history) < lookback:
        print(f"[{user['user_id']}] Not enough price history.")
        return

    trend_up = all(price_history[i] < price_history[i+1] for i in range(len(price_history)-1))
    trend_down = all(price_history[i] > price_history[i+1] for i in range(len(price_history)-1))

    current_price = price_history[-1]

    print(f"[{user['user_id']}] Price Trend: {price_history}")

    if trend_up:
        print(f"[{user['user_id']}] Momentum UP - BUY signal")
        trade_on_binance(user, action="buy", symbol=symbol, amount=risk)

    elif trend_down:
        print(f"[{user['user_id']}] Momentum DOWN - SELL signal")
        trade_on_binance(user, action="sell", symbol=symbol, amount=risk)

    else:
        print(f"[{user['user_id']}] No clear trend - no action")
