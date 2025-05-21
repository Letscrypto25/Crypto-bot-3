def execute(user):
    """
    User-configurable arbitrage strategy comparing Binance and Luno.
    Uses risk_tolerance and profit_target settings to guide trade decisions.
    """
    from trading_api import get_binance_price, get_luno_price, trade_on_binance, trade_on_luno

    symbol = "BTC/USDT"
    binance_price = get_binance_price(user, symbol)
    luno_price = get_luno_price(user, symbol)

    if not binance_price or not luno_price:
        print(f"[{user['user_id']}] Could not fetch prices.")
        return

    print(f"[{user['user_id']}] Binance: {binance_price} | Luno: {luno_price}")

    # Get user settings
    risk = float(user.get("risk_tolerance", 0.02))        # default 2%
    profit_target = float(user.get("profit_target", 50))  # default $50 spread
    print(f"[{user['user_id']}] Risk tolerance: {risk} | Profit target: {profit_target}")

    # Arbitrage logic based on price spread
    spread = abs(binance_price - luno_price)
    print(f"[{user['user_id']}] Spread: {spread}")

    if spread >= profit_target:
        if binance_price > luno_price:
            print(f"[{user['user_id']}] Arbitrage: Buy Luno, Sell Binance")
            trade_on_luno(user, action="buy", symbol=symbol)
            trade_on_binance(user, action="sell", symbol=symbol)
        else:
            print(f"[{user['user_id']}] Arbitrage: Buy Binance, Sell Luno")
            trade_on_binance(user, action="buy", symbol=symbol)
            trade_on_luno(user, action="sell", symbol=symbol)
    else:
        print(f"[{user['user_id']}] No arbitrage opportunity (target not met)")
