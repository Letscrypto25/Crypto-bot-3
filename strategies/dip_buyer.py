# strategies/dip_buyer.py

from firebase_admin import db
from trading_api import get_price_change, trade_on_binance

def execute(user):
    """
    Dip Buyer Strategy:
    Buy BTC when it drops significantly in a short time window (e.g., 15 minutes).
    Records profit and sends results to Firebase.
    """
    symbol = "BTC/USDT"
    interval = "15m"
    user_id = user["user_id"]

    threshold_drop = user.get("dip_threshold", -3.0)   # e.g. -3%
    risk = user.get("risk_tolerance", 0.02)            # % of capital to trade
    profit_target = user.get("profit_target", 50)      # Target profit in R

    change = get_price_change(user, symbol, interval=interval)

    if change is None:
        print(f"[{user_id}] Could not fetch price change.")
        update_trade_result(user_id, 0, "error")
        return

    print(f"[{user_id}] {interval} price change: {change:.2f}%")

    trade_result = "none"
    profit = 0

    if change <= threshold_drop:
        print(f"[{user_id}] Dip detected (≤ {threshold_drop}%) - BUY signal")
        success = trade_on_binance(user, action="buy", symbol=symbol, amount=risk)
        if success:
            profit = profit_target  # Simulated gain
            trade_result = "profit"
    else:
        print(f"[{user_id}] No dip detected")

    update_trade_result(user_id, profit, trade_result)


def update_trade_result(user_id, profit, status):
    """
    Update Firebase with profit and trade result.
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
