# utils/trade_utils.py
import logging 
from utils.firebase_utils import get_user_data, update_user_data
from utils.price_utils import get_current_price
from utils.time_utils import format_timestamp, get_utc_now
from utils.logger import get_logger

logger = get_logger("trade_utils")


def execute_trade(user_id: str, symbol: str, amount: float, trade_type: str) -> dict:
    user_data = get_user_data(user_id)
    if not user_data:
        logger.warning(f"Trade attempt for unregistered user: {user_id}")
        return {"success": False, "error": "User not registered."}

    balance = float(user_data.get("balance", 0))
    portfolio = user_data.get("portfolio", {})
    price = get_current_price(symbol)

    if price <= 0:
        logger.error(f"Failed to fetch price for {symbol}.")
        return {"success": False, "error": "Price fetch failed."}

    total_cost = amount * price
    fee = calculate_fees(total_cost)

    if trade_type == "buy":
        if balance < total_cost + fee:
            return {"success": False, "error": "Insufficient balance."}
        balance -= total_cost + fee
        portfolio[symbol] = portfolio.get(symbol, 0) + amount
        logger.info(f"{user_id} bought {amount} {symbol} at {price}, fee: {fee}")

    elif trade_type == "sell":
        if portfolio.get(symbol, 0) < amount:
            return {"success": False, "error": "Not enough assets to sell."}
        portfolio[symbol] -= amount
        balance += total_cost - fee
        logger.info(f"{user_id} sold {amount} {symbol} at {price}, fee: {fee}")

    else:
        return {"success": False, "error": "Invalid trade type."}

    # Update user data in Firebase
    update_user_data(user_id, {
        "balance": round(balance, 6),
        "portfolio": portfolio
    })

    # Log the trade
    record_trade(user_id, symbol, amount, price, trade_type, fee)

    return {"success": True}


def calculate_fees(value: float) -> float:
    """Calculates 0.1% fee."""
    return round(value * 0.001, 6)


def record_trade(user_id: str, symbol: str, amount: float, price: float, trade_type: str, fee: float):
    timestamp = format_timestamp(get_utc_now())
    trade_log = {
        "timestamp": timestamp,
        "symbol": symbol,
        "amount": amount,
        "price": price,
        "type": trade_type,
        "fee": fee,
        "total": round(amount * price, 6)
    }
    logger.info(f"Trade log for {user_id}: {trade_log}")
    log_trade(user_id, trade_log)
