import base64
import requests
from binance.client import Client

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

def get_luno_balance(api_key: str, api_secret: str) -> dict:
    auth_string = f"{api_key}:{api_secret}".encode()
    auth = base64.b64encode(auth_string).decode()
    headers = {"Authorization": f"Basic {auth}"}

    try:
        response = requests.get("https://api.luno.com/api/1/balance", headers=headers)
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

def get_balance(user_id: str, source: str, user: dict) -> dict:
    """
    Fetch balance for a user from the specified exchange.
    
    :param user_id: Unique user ID (string)
    :param source: 'luno' or 'binance'
    :param user: Dictionary containing API keys
    :return: Dictionary of balances
    """
    if source == "luno":
        return get_luno_balance(user["luno_api_key"], user["luno_api_secret"])
    elif source == "binance":
        return get_binance_balance(user["binance_api_key"], user["binance_api_secret"])
    else:
        print(f"[Error] Unknown exchange source: {source}")
        return {}

# Example usage
if __name__ == "__main__":
    user_data = {
        "luno_api_key": "your_luno_api_key",
        "luno_api_secret": "your_luno_api_secret",
        "binance_api_key": "your_binance_api_key",
        "binance_api_secret": "your_binance_api_secret",
    }

    user_id = "user123"

    luno_balances = get_balance(user_id, "luno", user_data)
    print("Luno Balances:", luno_balances)

    binance_balances = get_balance(user_id, "binance", user_data)
    print("Binance Balances:", binance_balances)
