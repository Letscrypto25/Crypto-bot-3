import logging
import requests
from binance.client import Client as BinanceClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --- Binance Price Fetcher ---
def get_binance_price(symbol="BTC/USDT", api_key=None, api_secret=None):
    """
    Fetch the current market price of a trading pair from Binance.
    Accepts 'BTC/USDT' or 'ETH/BTC' formats.
    """
    try:
        client = BinanceClient(api_key=api_key, api_secret=api_secret)
        symbol_binance = symbol.replace("/", "")  # Convert 'BTC/USDT' to 'BTCUSDT'
        ticker = client.get_symbol_ticker(symbol=symbol_binance)
        price = float(ticker['price'])
        logger.info(f"Binance price for {symbol}: {price}")
        return price
    except Exception as e:
        logger.error(f"Failed to get Binance price for {symbol}: {e}")
        return None

# --- Luno Price Fetcher ---
def get_luno_price(pair="XBTZAR"):
    """
    Fetch the current market price from Luno.
    """
    try:
        response = requests.get(f"https://api.luno.com/api/1/ticker?pair={pair}")
        response.raise_for_status()
        data = response.json()
        price = float(data.get("last_trade"))
        logger.info(f"Luno price for {pair}: {price}")
        return price
    except Exception as e:
        logger.error(f"Failed to get Luno price for {pair}: {e}")
        return None
