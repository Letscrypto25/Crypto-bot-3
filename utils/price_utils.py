# utils/price_utils.py

import requests
from utils.logger import get_logger

logger = get_logger("price_utils")

def get_current_price(symbol: str) -> float:
    """
    Fetches the current price of a crypto asset from Binance.
    Symbol should be in format: BTCUSDT, ETHUSDT, etc.
    """
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol.upper()}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        price = float(data["price"])
        logger.info(f"Fetched price for {symbol}: {price}")
        return price
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}")
        return 0.0
