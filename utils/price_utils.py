# utils/price_utils.py

import requests
from utils.logger import get_logger
from requests.auth import HTTPBasicAuth

logger = get_logger("price_utils")

def get_price(symbol: str,
               binance_api_key: str = None,
               binance_api_secret: str = None,
               luno_api_key: str = None,
               luno_api_secret: str = None) -> float:
    """
    Fetches the current price of a crypto asset from Binance or Luno.
    Priority is Binance if both APIs are provided.
    Symbol should be in format: BTCUSDT for Binance, or XBTZAR for Luno.
    """
    try:
        if binance_api_key and binance_api_secret:
            # Use Binance API (public endpoint; no need for API key in this specific call)
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol.upper()}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            price = float(data["price"])
            logger.info(f"Fetched price from Binance for {symbol}: {price}")
            return price

        elif luno_api_key and luno_api_secret:
            # Use Luno API (authentication needed)
            pair = symbol.upper()
            url = f"https://api.luno.com/api/1/ticker?pair={pair}"
            response = requests.get(url, auth=HTTPBasicAuth(luno_api_key, luno_api_secret), timeout=10)
            response.raise_for_status()
            data = response.json()
            price = float(data["last_trade"])
            logger.info(f"Fetched price from Luno for {symbol}: {price}")
            return price

        else:
            logger.error("No API credentials provided for Binance or Luno.")
            return 0.0

    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}")
        return 0.0
