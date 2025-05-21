# strategies/momentum.py

from firebase_admin import db
from trading_api import get_price_history, trade_on_binance

def execute(user):
    """
    Momentum Strategy:
    Buy if price trending up, sell if trending down.
    Simulates profit and updates Firebase.
    """
    symbol = "BTC/USDT"
    interval = "1m"
    lookback = 5
    user_id = user["user_id"]

    risk = user.get("risk_tolerance", 0.02)
    profit_target = user.get("profit_target", 50)

    price_history = get_price_history(user, symbol, interval, lookback)

    if not price_history or len(price_history) < lookback:
        print(f"[{user_id}] Not enough price history.")
        update_trade_result(user_id, 0, "error")
        return

    trend_up = all(price_history[i] < price_history[i + 1] for i in range(len(price_history) - 1))
    trend_down = all(price_history[i] > price_history[i + 1] for i in range(len(price_history) - 1))

    print(f"[{user_id}] Price Trend: {price_history}")

    trade_result = "none"
    profit = 0

    if trend_up:
        print(f"[{user_id}] Momentum UP - BUY signal")
        success = trade_on_binance(user, action="buy", symbol=symbol, amount=risk)
        if success:
            profit = profit_target
            trade_result = "profit"

    elif trend_down:
        print(f"[{user_id}] Momentum DOWN - SELL signal")
        success = trade_on_binance(user, action="sell", symbol=symbol, amount=risk)
        if success:
            profit = profit_target
            trade_result = "profit"

    else:
        print(f"[{user_id}] No clear trend - no action")

    update_trade_result(user_id, profit, trade_result)


def update_trade_result(user_id, profit, status):
    """
    Update Firebase with trade result and profit.
    """
    try:
        user_ref = db.reference(f"/users/{user_id}")
        current_profit = user_ref.child("daily_profit").get() or 0
        user_ref.update({
            "daily_profit": round(current_profit + profit, 2),
            "last_trade_result": status
        })
    except Exception as e:
        print(f"[{user_id}] Error updating trade result: {e}")
