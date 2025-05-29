from firebase_admin import db
from trading_api import (
    get_binance_price,
    get_luno_price,
    trade_on_binance,
    trade_on_luno,
    get_balance
)

def execute(user):
    """
    Arbitrage strategy that compares Binance and Luno prices,
    and updates daily profit stats + trade result status in Firebase.
    """
    symbol = "BTC/USDT"
    user_id = user["user_id"]
    platform = user.get("platform", "luno")

    # Settings with defaults
    risk_tolerance = user.get("risk_tolerance", 0.02)  # 2%
    profit_target = user.get("profit_target", 50)      # Minimum profit threshold in ZAR

    # Check user balance (assumes get_balance returns ZAR equivalent)
    balance = get_balance(user, platform)
    if balance < 100:
        print(f"[{user_id}] ✋ You need at least R100 to activate autobot. Chill and top up your wallet 😎")
        update_trade_result(user_id, 0, "low_balance")
        return

    try:
        binance_price = get_binance_price(user, symbol)
        luno_price = get_luno_price(user, symbol)

        if not binance_price or not luno_price:
            print(f"[{user_id}] Error: Could not fetch one or both prices.")
            update_trade_result(user_id, 0, "error")
            return

        print(f"[{user_id}] Binance: {binance_price} | Luno: {luno_price}")

        price_diff = abs(binance_price - luno_price)
        trade_result = "none"
        profit = 0

        if binance_price > luno_price + profit_target:
            print(f"[{user_id}] Arbitrage Opportunity: Buy on Luno, Sell on Binance")
            profit, trade_result = attempt_arbitrage_trade(
                user, "luno", "binance", symbol, risk_tolerance, price_diff
            )

        elif luno_price > binance_price + profit_target:
            print(f"[{user_id}] Arbitrage Opportunity: Buy on Binance, Sell on Luno")
            profit, trade_result = attempt_arbitrage_trade(
                user, "binance", "luno", symbol, risk_tolerance, price_diff
            )

        else:
            print(f"[{user_id}] No arbitrage opportunity (Diff: {price_diff:.2f})")

        update_trade_result(user_id, profit, trade_result)

    except Exception as e:
        print(f"[{user_id}] Arbitrage strategy failed: {e}")
        update_trade_result(user_id, 0, "error")


def attempt_arbitrage_trade(user, buy_exchange, sell_exchange, symbol, risk, profit_value):
    """
    Helper function to execute buy and sell on specified exchanges.
    Returns (profit, trade_result)
    """
    user_id = user["user_id"]
    platform = user.get("platform", "luno")

    balance = get_balance(user, platform)
    if balance < 50:
        print(f"[{user_id}] Minimum trade amount is R50. Current balance: R{balance:.2f}. No trade executed 🌱")
        return 0, "low_trade_balance"

    try:
        buy_func = trade_on_binance if buy_exchange == "binance" else trade_on_luno
        sell_func = trade_on_binance if sell_exchange == "binance" else trade_on_luno

        success_buy = buy_func(user, action="buy", symbol=symbol, risk_tolerance=risk)
        success_sell = sell_func(user, action="sell", symbol=symbol, risk_tolerance=risk)

        if success_buy and success_sell:
            return round(profit_value, 2), "profit"
        else:
            return 0, "failed"

    except Exception as e:
        print(f"[{user_id}] Trade execution error: {e}")
        return 0, "error"


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
