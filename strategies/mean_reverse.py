from firebase_admin import db
from trading_api import get_price_history, trade_on_binance

def execute(user):
    """
    Mean Reversion Strategy:
    Trades when the current price deviates significantly from its recent average,
    expecting a reversion to the mean. Updates results in Firebase.
    """
    symbol = "BTC/USDT"
    interval = "1m"
    lookback = 10
    user_id = user["user_id"]

    risk = user.get("risk_tolerance", 0.02)
    profit_target = user.get("profit_target", 50)

    try:
        price_history = get_price_history(user, symbol, interval, lookback)

        if not price_history or len(price_history) < lookback:
            print(f"[{user_id}] Not enough data for mean reversion strategy.")
            update_trade_result(user_id, 0, "error")
            return

        current_price = price_history[-1]
        mean_price = sum(price_history[:-1]) / (len(price_history) - 1)
        deviation = (current_price - mean_price) / mean_price

        print(f"[{user_id}] Current: {current_price:.2f} | Mean: {mean_price:.2f} | Deviation: {deviation:.4f}")

        trade_result = "none"
        profit = 0

        if deviation > 0.01:
            print(f"[{user_id}] Price above mean → SELL")
            success = trade_on_binance(user, action="sell", symbol=symbol, amount=risk)
            if success:
                profit = profit_target
                trade_result = "profit"

        elif deviation < -0.01:
            print(f"[{user_id}] Price below mean → BUY")
            success = trade_on_binance(user, action="buy", symbol=symbol, amount=risk)
            if success:
                profit = profit_target
                trade_result = "profit"

        else:
            print(f"[{user_id}] No significant deviation → No trade")

        update_trade_result(user_id, profit, trade_result)

    except Exception as e:
        print(f"[{user_id}] Mean Reversion strategy error: {e}")
        update_trade_result(user_id, 0, "error")


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
