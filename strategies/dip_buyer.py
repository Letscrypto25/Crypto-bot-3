def execute(user):
    """
    Dip Buyer Strategy:
    Buy BTC when it drops significantly in a short time window (e.g., 15 minutes).
    """
    from trading_api import get_price_change, trade_on_binance

    symbol = "BTC/USDT"
    interval = "15m"
    threshold_drop = user.get("dip_threshold", -3.0)  # user-defined or default -3%
    risk = user.get("risk_tolerance", 0.02)  # % of capital to trade

    change = get_price_change(user, symbol, interval=interval)

    if change is None:
        print(f"[{user['user_id']}] Could not fetch price change.")
        return

    print(f"[{user['user_id']}] {interval} price change: {change:.2f}%")

    if change <= threshold_drop:
        print(f"[{user['user_id']}] Dip detected (≤ {threshold_drop}%) - BUY signal")
        trade_on_binance(user, action="buy", symbol=symbol, amount=risk)
    else:
        print(f"[{user['user_id']}] No dip detected")
