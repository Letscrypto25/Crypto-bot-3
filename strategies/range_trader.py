# strategies/range_trader.py

def execute(user):
    from trading_api import get_binance_price, trade_on_binance

    symbol = "BTC/USDT"
    price = get_binance_price(user, symbol)

    if not price:
        print(f"[{user['user_id']}] Could not fetch price.")
        return

    lower_bound = 29500
    upper_bound = 30500

    print(f"[{user['user_id']}] Price: {price}")

    if price < lower_bound:
        print(f"[{user['user_id']}] Buying at low range")
        trade_on_binance(user, action="buy", symbol=symbol)
    elif price > upper_bound:
        print(f"[{user['user_id']}] Selling at high range")
        trade_on_binance(user, action="sell", symbol=symbol)
    else:
        print(f"[{user['user_id']}] Price in middle of range — holding")
