import base64
import requests
from binance.client import Client

async def get_balance(source: str, user_id: str = None, user=None,
                       luno_api_key=None, luno_api_secret=None,
                       binance_api_key=None, binance_api_secret=None) -> dict:
    print(f"Fetching balance for user: {user_id} on {source}")

    try:
        if source == "luno":
            key = luno_api_key
            secret = luno_api_secret
            auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
            headers = {"Authorization": f"Basic {auth}"}
            r = requests.get("https://api.luno.com/api/1/balance", headers=headers)
            print("Luno response:", r.text)
            r.raise_for_status()
            data = r.json().get("balance", [])
            return {
                asset["asset"]: float(asset["balance"])
                for asset in data
                if float(asset["balance"]) > 0
            }

        elif source == "binance":
            client = Client(binance_api_key, binance_api_secret)
            raw_balances = client.get_account()["balances"]
            print("Binance balances:", raw_balances)
            return {
                b["asset"]: float(b["free"])
                for b in raw_balances
                if float(b["free"]) > 0
            }

        else:
            raise ValueError(f"Unknown exchange source: {source}")

    except Exception as e:
        print(f"[Balance Fetch Error for user {user_id}] {e}")
        return {}
