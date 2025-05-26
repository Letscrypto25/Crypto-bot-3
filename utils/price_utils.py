# utils/price_utils.py

import requests

def get_current_price(symbol: str) -> float:
    """
    Fetches the current price of a crypto asset from Binance.
    Symbol should be in format: BTCUSDT, ETHUSDT, etc.
    """
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol.upper()}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return float(data["price"])
    except Exception as e:
        print(f"[price_utils] Error fetching price for {symbol}: {e}")
        return 0.0
