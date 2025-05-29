import logging
from binance.client import Client as BinanceClient
import requests
import hmac
import hashlib
import time

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def get_user_balance(user_id, platform, user_data=None):
    """Fetches real balance for the given platform and user."""
    if platform.lower() == "binance":
        return get_binance_balance(user_data)
    elif platform.lower() == "luno":
        return get_luno_balance(user_data)
    else:
        raise ValueError(f"Unsupported platform: {platform}")

def get_binance_balance(user):
    """Returns available balance for Binance using API key/secret."""
    try:
        client = BinanceClient(user["binance_api_key"], user["binance_api_secret"])
        account_info = client.get_account()
        balances = {item['asset']: float(item['free']) for item in account_info['balances'] if float(item['free']) > 0}
        return balances
    except Exception as e:
        logger.error(f"[{user['user_id']}] Binance balance fetch error: {e}")
        return {}

def get_luno_balance(user):
    """Returns available balance for Luno using API key/secret."""
    try:
        url = "https://api.luno.com/api/1/balance"
        nonce = str(int(time.time() * 1000))
        auth = (user["luno_api_key"], user["luno_api_secret"])
        response = requests.get(url, auth=auth)
        response.raise_for_status()
        data = response.json()
        balances = {item['asset']: float(item['balance']) for item in data['balance'] if float(item['balance']) > 0}
        return balances
    except Exception as e:
        logger.error(f"[{user['user_id']}] Luno balance fetch error: {e}")
        return {}
