# strategies/trend_follow.py

def execute(user):
    from trading_api import get_moving_average, get_binance_price, trade_on_binance

    symbol = "BTC/USDT"

    price = get_binance_price(user, symbol)
    ma_20 = get_moving_average(user, symbol, period=20)
    ma_50 = get_moving_average(user, symbol, period=50)

    if None in (price, ma_20, ma_50):
        print(f"[{user['user_id']}] Could not fetch trend data.")
        return

    print(f"[{user['user_id']}] Price: {price} | MA20: {ma_20} | MA50: {ma_50}")

    if ma_20 > ma_50 and price > ma_20:
        print(f"[{user['user_id']}] Uptrend detected — buying")
        trade_on_binance(user, action="buy", symbol=symbol)
    elif ma_20 < ma_50 and price < ma_20:
        print(f"[{user['user_id']}] Downtrend detected — selling")
        trade_on_binance(user, action="sell", symbol=symbol)
    else:
        print(f"[{user['user_id']}] No clear trend")

