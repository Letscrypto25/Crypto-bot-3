import base64
import requests
from binance.client import Client

# 🟩 Binance balance fetcher
def get_binance_balance(api_key: str, api_secret: str) -> dict:
    client = Client(api_key, api_secret)
    try:
        account_info = client.get_account()
        balances = {
            b["asset"]: float(b["free"])
            for b in account_info.get("balances", [])
            if float(b["free"]) > 0
        }
        return balances
    except Exception as e:
        print(f"[Binance Error] {e}")
        return {}

# 🟩 Updated Luno balance fetcher with debug info and User-Agent header
def get_luno_balance(api_key: str, api_secret: str) -> dict:
    auth_string = f"{api_key}:{api_secret}".encode()
    auth = base64.b64encode(auth_string).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "User-Agent": "Mozilla/5.0 (compatible; MyApp/1.0; +https://myapp.com)"
    }

    try:
        response = requests.get("https://api.luno.com/api/1/balance", headers=headers)
        print(f"[Luno] Response status: {response.status_code}")
        print(f"[Luno] Response text: {response.text}")
        response.raise_for_status()

        data = response.json().get("balance", [])
        balances = {
            asset["asset"]: float(asset["balance"])
            for asset in data
            if float(asset["balance"]) > 0
        }
        return balances
    except Exception as e:
        print(f"[Luno Error] {e}")
        return {}

# 🟩 Unified balance fetcher — expects decrypted keys
def get_balance(user_id: str, source: str, user: dict) -> dict:
    """
    Fetch balance for a user from the specified exchange.

    :param user_id: Unique user ID (string)
    :param source: 'luno' or 'binance'
    :param user: Dictionary containing PLAINTEXT API keys
    :return: Dictionary of balances
    """
    try:
        if source == "luno":
            return get_luno_balance(user["luno_api_key"], user["luno_api_secret"])

        elif source == "binance":
            return get_binance_balance(user["binance_api_key"], user["binance_api_secret"])

        else:
            print(f"[Error] Unknown exchange source: {source}")
            return {}

    except Exception as e:
        print(f"[Balance Fetch Error] {source}: {e}")
        return {}
