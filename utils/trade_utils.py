# utils/trade_utils.py

from utils.firebase_utils import get_user_data, update_user_data
from utils.price_utils import get_current_price
from utils.time_utils import get_timestamp
from utils.logger import log_trade

def execute_trade(user_id: str, symbol: str, amount: float, trade_type: str) -> dict:
    user_data = get_user_data(user_id)
    if not user_data:
        return {"success": False, "error": "User not registered."}

    balance = float(user_data.get("balance", 0))
    portfolio = user_data.get("portfolio", {})
    price = get_current_price(symbol)
    total_cost = amount * price
    fee = calculate_fees(total_cost)

    if trade_type == "buy":
        if balance < total_cost + fee:
            return {"success": False, "error": "Insufficient balance."}
        balance -= total_cost + fee
        portfolio[symbol] = portfolio.get(symbol, 0) + amount

    elif trade_type == "sell":
        if portfolio.get(symbol, 0) < amount:
            return {"success": False, "error": "Not enough assets to sell."}
        portfolio[symbol] -= amount
        balance += total_cost - fee

    else:
        return {"success": False, "error": "Invalid trade type."}

    # Update user data
    update_user_data(user_id, {
        "balance": balance,
        "portfolio": portfolio
    })

    # Log trade
    record_trade(user_id, symbol, amount, price, trade_type, fee)

    return {"success": True}

def calculate_fees(value: float) -> float:
    return round(value * 0.001, 6)  # Example: 0.1% fee

def record_trade(user_id: str, symbol: str, amount: float, price: float, trade_type: str, fee: float):
    timestamp = get_timestamp()
    trade_log = {
        "timestamp": timestamp,
        "symbol": symbol,
        "amount": amount,
        "price": price,
        "type": trade_type,
        "fee": fee,
        "total": amount * price
    }
    log_trade(user_id, trade_log)
