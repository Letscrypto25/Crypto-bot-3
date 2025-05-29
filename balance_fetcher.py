import logging
import requests
from binance.client import Client
from firebase_admin import db

logger = logging.getLogger(__name__)

def get_user_balance(user_id, platform):
    """Fetch user balances from Binance or Luno."""
    user_ref = db.reference(f"/users/{user_id}")
    user_data = user_ref.get()

    if not user_data:
        raise ValueError(f"User {user_id} not found")

    if platform.lower() == "binance":
        return get_binance_balance(user_data)
    elif platform.lower() == "luno":
        return get_luno_balance(user_data)
    else:
        raise ValueError(f"Unknown platform '{platform}'")

def get_binance_balance(user_data):
    api_key = user_data["binance_api_key"]
    api_secret = user_data["binance_api_secret"]
    client = Client(api_key, api_secret)

    account_info = client.get_account()
    balances = account_info.get("balances", [])
    
    result = {}
    for asset in balances:
        asset_name = asset["asset"]
        free = float(asset["free"])
        if free > 0:
            result[asset_name] = free
    return result

def get_luno_balance(user_data):
    api_key = user_data["luno_api_key"]
    api_secret = user_data["luno_api_secret"]

    response = requests.get(
        "https://api.luno.com/api/1/balance",
        auth=(api_key, api_secret)
    )
    if response.status_code != 200:
        raise Exception(f"Luno balance fetch failed: {response.text}")

    balances = response.json().get("balance", [])
    result = {}
    for item in balances:
        asset = item["asset"]
        balance = float(item["balance"])
        if balance > 0:
            result[asset] = balance
    return result
