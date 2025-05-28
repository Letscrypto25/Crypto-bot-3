from firebase_admin import db
from trading_api import get_price_change, trade_on_binance

def execute(user):
    """
    Dip Buyer Strategy:
    Buys BTC when there's a significant short-term drop.
    Updates profit and trade results in Firebase.
    """
    symbol = "BTC/USDT"
    interval = "15m"
    user_id = user["user_id"]

    threshold_drop = user.get("dip_threshold", -3.0)   # Trigger dip at -3% or lower
    risk = user.get("risk_tolerance", 0.02)            # % of capital to trade
    profit_target = user.get("profit_target", 50)      # Simulated gain for success (in ZAR/USD/etc.)

    try:
        change = get_price_change(user, symbol, interval=interval)

        if change is None:
            print(f"[{user_id}] Error: Could not fetch price change for dip strategy.")
            update_trade_result(user_id, 0, "error")
            return

        print(f"[{user_id}] {interval} price change: {change:.2f}%")

        trade_result = "none"
        profit = 0

        if change <= threshold_drop:
            print(f"[{user_id}] Dip detected (≤ {threshold_drop}%) - executing BUY")
            success = trade_on_binance(user, action="buy", symbol=symbol, amount=risk)
            if success:
                profit = profit_target
                trade_result = "profit"
            else:
                trade_result = "failed"
        else:
            print(f"[{user_id}] No dip detected")

        update_trade_result(user_id, profit, trade_result)

    except Exception as e:
        print(f"[{user_id}] Dip buyer strategy failed: {e}")
        update_trade_result(user_id, 0, "error")


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
