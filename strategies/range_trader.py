from trading_api import get_rsi, trade_on_binance
from notifications import notify_user_profit_loss
from firebase_admin import db
import time

def execute(user):
    """
    RSI Strategy:
    - Buy when RSI < oversold threshold
    - Sell when RSI > overbought threshold
    Logs result to Firebase and notifies user.
    """
    symbol = "BTC/USDT"
    period = user.get("rsi_period", 14)
    oversold = user.get("rsi_oversold", 30)
    overbought = user.get("rsi_overbought", 70)
    risk = user.get("risk_tolerance", 0.02)
    user_id = user["user_id"]

    try:
        rsi = get_rsi(user, symbol, period)
        if rsi is None:
            print(f"[{user_id}] RSI fetch failed.")
            return

        print(f"[{user_id}] RSI({period}): {rsi}")
        action = None

        if rsi < oversold:
            action = "buy"
            print(f"[{user_id}] RSI < {oversold} → BUY signal")
        elif rsi > overbought:
            action = "sell"
            print(f"[{user_id}] RSI > {overbought} → SELL signal")
        else:
            print(f"[{user_id}] RSI neutral → no trade")
            return

        # Execute trade
        profit_or_loss = trade_on_binance(user, action=action, symbol=symbol, amount=risk)

        # Log trade to Firebase
        try:
            trades_ref = db.reference(f"/users/{user_id}/trades")
            trades_ref.push({
                "timestamp": int(time.time()),
                "strategy": "rsi",
                "action": action,
                "profit_or_loss": round(profit_or_loss, 2),
            })
        except Exception as e:
            print(f"[{user_id}] Firebase logging error: {e}")

        # Notify user
        notify_user_profit_loss(user_id, action, profit_or_loss)

    except Exception as e:
        print(f"[{user_id}] RSI strategy error: {e}")
