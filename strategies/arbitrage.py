# strategies/arbitrage.py

from firebase_admin import db
from trading_api import get_binance_price, get_luno_price, trade_on_binance, trade_on_luno

def execute(user):
    """
    Arbitrage strategy that compares Binance and Luno prices,
    and updates daily profit stats + trade result status in Firebase.
    """
    symbol = "BTC/USDT"

    # User-defined or default settings
    risk_tolerance = user.get("risk_tolerance", 0.02)  # 2%
    profit_target = user.get("profit_target", 50)      # R50

    user_id = user["user_id"]
    binance_price = get_binance_price(user, symbol)
    luno_price = get_luno_price(user, symbol)

    if not binance_price or not luno_price:
        print(f"[{user_id}] Could not fetch prices.")
        update_trade_result(user_id, 0, "error")
        return

    print(f"[{user_id}] Binance: {binance_price} | Luno: {luno_price}")

    price_diff = abs(binance_price - luno_price)
    threshold = profit_target

    trade_result = "none"
    profit = 0

    if binance_price > luno_price + threshold:
        print(f"[{user_id}] Arbitrage: Buy Luno, Sell Binance")
        success_buy = trade_on_luno(user, action="buy", symbol=symbol, risk_tolerance=risk_tolerance)
        success_sell = trade_on_binance(user, action="sell", symbol=symbol, risk_tolerance=risk_tolerance)
        if success_buy and success_sell:
            profit = price_diff
            trade_result = "profit"

    elif luno_price > binance_price + threshold:
        print(f"[{user_id}] Arbitrage: Buy Binance, Sell Luno")
        success_buy = trade_on_binance(user, action="buy", symbol=symbol, risk_tolerance=risk_tolerance)
        success_sell = trade_on_luno(user, action="sell", symbol=symbol, risk_tolerance=risk_tolerance)
        if success_buy and success_sell:
            profit = price_diff
            trade_result = "profit"

    else:
        print(f"[{user_id}] No arbitrage opportunity")

    update_trade_result(user_id, profit, trade_result)


def update_trade_result(user_id, profit, status):
    """
    Update Firebase with profit and result of the trade.
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
