import logging
import requests
import time
from binance.client import Client as BinanceClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price?ids={}&vs_currencies=zar"

def get_user_balance(user_id, platform, user_data=None):
    """Fetches real balance in ZAR for the given platform and user."""
    if platform.lower() == "binance":
        balances = get_binance_balance(user_data)
    elif platform.lower() == "luno":
        balances = get_luno_balance(user_data)
    else:
        raise ValueError(f"Unsupported platform: {platform}")

    total_zar = convert_balances_to_zar(balances)
    return {"ZAR": total_zar, **balances}


def get_binance_balance(user):
    """Fetch real Binance balance using API key/secret."""
    try:
        client = BinanceClient(user["binance_api_key"], user["binance_api_secret"])
        account_info = client.get_account()
        return {b["asset"]: float(b["free"]) for b in account_info["balances"] if float(b["free"]) > 0}
    except Exception as e:
        logger.error(f"[{user['user_id']}] Binance error: {e}")
        return {}


def get_luno_balance(user):
    """Fetch real Luno balance using API key/secret."""
    try:
        url = "https://api.luno.com/api/1/balance"
        auth = (user["luno_api_key"], user["luno_api_secret"])
        res = requests.get(url, auth=auth)
        res.raise_for_status()
        data = res.json()
        return {b["asset"]: float(b["balance"]) for b in data["balance"] if float(b["balance"]) > 0}
    except Exception as e:
        logger.error(f"[{user['user_id']}] Luno error: {e}")
        return {}


def convert_balances_to_zar(balances):
    """Convert all crypto balances to ZAR value using live rates."""
    total = 0
    for asset, amount in balances.items():
        if asset == "ZAR":
            total += amount
        else:
            price = fetch_price_in_zar(asset)
            if price:
                total += amount * price
    return round(total, 2)


def fetch_price_in_zar(asset_symbol):
    """Fetch asset price in ZAR using Binance or fallback to Coingecko."""
    symbol = asset_symbol.upper() + "ZAR"

    try:
        # Try Binance first
        res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
        if res.status_code == 200:
            return float(res.json()["price"])
    except:
        pass

    try:
        # Fallback to Coingecko
        mapping = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "USDT": "tether",
            "BNB": "binancecoin",
            "XRP": "ripple",
            "SOL": "solana",
            "LTC": "litecoin",
            "DOGE": "dogecoin",
        }
        coin_id = mapping.get(asset_symbol.upper())
        if not coin_id:
            return 0
        res = requests.get(COINGECKO_API.format(coin_id))
        if res.status_code == 200:
            return res.json()[coin_id]["zar"]
    except:
        pass

    return 0
