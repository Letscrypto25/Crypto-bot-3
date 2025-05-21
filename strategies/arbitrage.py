# strategies/arbitrage.py

def execute(user):
    """
    Basic arbitrage strategy that compares Binance and Luno prices.
    This function is called by the auto bot for each user.
    """
    from trading_api import get_binance_price, get_luno_price, trade_on_binance, trade_on_luno

    symbol = "BTC/USDT"

    binance_price = get_binance_price(user, symbol)
    luno_price = get_luno_price(user, symbol)

    if not binance_price or not luno_price:
        print(f"[{user['user_id']}] Could not fetch prices.")
        return

    print(f"[{user['user_id']}] Binance: {binance_price} | Luno: {luno_price}")

    # If price difference is big enough, trade
    threshold = 50  # Minimum profit difference to trigger a trade

    if binance_price > luno_price + threshold:
        print(f"[{user['user_id']}] Arbitrage: Buy Luno, Sell Binance")
        trade_on_luno(user, action="buy", symbol=symbol)
        trade_on_binance(user, action="sell", symbol=symbol)

    elif luno_price > binance_price + threshold:
        print(f"[{user['user_id']}] Arbitrage: Buy Binance, Sell Luno")
        trade_on_binance(user, action="buy", symbol=symbol)
        trade_on_luno(user, action="sell", symbol=symbol)

    else:
        print(f"[{user['user_id']}] No arbitrage opportunity")
