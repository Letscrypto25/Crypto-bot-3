from firebase_admin import db
from trading_api import get_price_history, trade_on_binance, get_user_balance

def execute(user):
    """
    Momentum Strategy:
    Buys if short-term prices are consistently rising,
    sells if consistently falling. Requires R100+ balance and R50+ trade size.
    Updates Firebase with trade results.
    """
    symbol = "BTC/USDT"
    interval = "1m"
    lookback = 5
    user_id = user["user_id"]

    risk = user.get("risk_tolerance", 0.02)
    profit_target = user.get("profit_target", 50)

    try:
        # 💰 Balance check
        balance = get_user_balance(user)
        if balance is None or balance < 100:
            print(f"[{user_id}] Balance too low (R{balance}) — Need at least R100 to trade.")
            update_trade_result(user_id, 0, "low_balance")
            return

        # 📈 Price history
        price_history = get_price_history(user, symbol, interval, lookback)
        if not price_history or len(price_history) < lookback:
            print(f"[{user_id}] Not enough price history for momentum strategy.")
            update_trade_result(user_id, 0, "error")
            return

        print(f"[{user_id}] Price Trend: {price_history}")

        trend_up = all(price_history[i] < price_history[i + 1] for i in range(len(price_history) - 1))
        trend_down = all(price_history[i] > price_history[i + 1] for i in range(len(price_history) - 1))

        trade_result = "none"
        profit = 0

        # 📈 Buy signal
        if trend_up:
            if balance * risk < 50:
                print(f"[{user_id}] Not enough to buy. R{balance * risk:.2f} < R50 minimum.")
                update_trade_result(user_id, 0, "min_trade_not_met")
                return

            print(f"[{user_id}] Momentum UP → BUY signal")
            success = trade_on_binance(user, action="buy", symbol=symbol, amount=risk)
            if success:
                profit = profit_target
                trade_result = "profit"

        # 📉 Sell signal
        elif trend_down:
            if balance * risk < 50:
                print(f"[{user_id}] Not enough to sell. R{balance * risk:.2f} < R50 minimum.")
                update_trade_result(user_id, 0, "min_trade_not_met")
                return

            print(f"[{user_id}] Momentum DOWN → SELL signal")
            success = trade_on_binance(user, action="sell", symbol=symbol, amount=risk)
            if success:
                profit = profit_target
                trade_result = "profit"

        else:
            print(f"[{user_id}] No strong momentum detected → No trade")

        update_trade_result(user_id, profit, trade_result)

    except Exception as e:
        print(f"[{user_id}] Momentum strategy error: {e}")
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
