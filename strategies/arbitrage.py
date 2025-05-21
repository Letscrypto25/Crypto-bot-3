# strategies/arbitrage.py

def execute(user):
    """
    Basic arbitrage strategy that compares Binance and Luno prices.
    Uses user-specific settings for risk tolerance and profit target.
    """
    from trading_api import get_binance_price, get_luno_price, trade_on_binance, trade_on_luno

    symbol = "BTC/USDT"

    # Default settings if user has none set
    risk_tolerance = user.get("risk_tolerance", 0.02)  # 2%
    profit_target = user.get("profit_target", 50)      # $50

    binance_price = get_binance_price(user, symbol)
    luno_price = get_luno_price(user, symbol)

    if not binance_price or not luno_price:
        print(f"[{user['user_id']}] Could not fetch prices.")
        return

    print(f"[{user['user_id']}] Binance: {binance_price} | Luno: {luno_price}")

    price_diff = abs(binance_price - luno_price)

    # Adjust threshold dynamically based on user profit target
    threshold = profit_target

    if binance_price > luno_price + threshold:
        print(f"[{user['user_id']}] Arbitrage: Buy Luno, Sell Binance")
        trade_on_luno(user, action="buy", symbol=symbol, risk_tolerance=risk_tolerance)
        trade_on_binance(user, action="sell", symbol=symbol, risk_tolerance=risk_tolerance)

    elif luno_price > binance_price + threshold:
        print(f"[{user['user_id']}] Arbitrage: Buy Binance, Sell Luno")
        trade_on_binance(user, action="buy", symbol=symbol, risk_tolerance=risk_tolerance)
        trade_on_luno(user, action="sell", symbol=symbol, risk_tolerance=risk_tolerance)

    else:
        print(f"[{user['user_id']}] No arbitrage opportunity")
