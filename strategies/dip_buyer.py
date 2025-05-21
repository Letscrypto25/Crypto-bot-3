# strategies/dip_buyer.py

def execute(user):
    from trading_api import get_price_change, trade_on_binance

    symbol = "BTC/USDT"
    threshold_drop = -3.0  # % drop

    change = get_price_change(user, symbol, interval="15m")

    if change is None:
        print(f"[{user['user_id']}] Could not fetch price change.")
        return

    print(f"[{user['user_id']}] 15m price change: {change:.2f}%")

    if change < threshold_drop:
        print(f"[{user['user_id']}] Dip detected, buying BTC")
        trade_on_binance(user, action="buy", symbol=symbol)
    else:
        print(f"[{user['user_id']}] No dip detected")

