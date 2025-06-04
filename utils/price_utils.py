# utils/price_utils.py

import requests
from utils.logger import get_logger

logger = get_logger("price_utils")

def get_price(symbol: str, platform: str = "binance") -> float:
    """
    Fetches the current price of a crypto asset.
    :param symbol: e.g., BTCUSDT, ETHUSDT for Binance;
                    BTCZAR, ETHZAR for Luno
    :param platform: "binance" or "luno"
    """
    try:
        if platform.lower() == "binance":
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol.upper()}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            price = float(data["price"])
            logger.info(f"Fetched Binance price for {symbol}: {price}")
            return price

        elif platform.lower() == "luno":
            # Luno uses a different endpoint and symbol format
            url = f"https://api.luno.com/api/1/ticker?pair={symbol.lower()}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            price = float(data["last_trade"])
            logger.info(f"Fetched Luno price for {symbol}: {price}")
            return price

        else:
            logger.warning(f"Unsupported platform: {platform}")
            return 0.0

    except Exception as e:
        logger.error(f"Error fetching price for {symbol} on {platform}: {e}")
        return 0.0
