import base64
import requests
from binance.client import Client
from encryption import decrypt_data

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

# 🟩 Luno balance fetcher
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

# 🟩 Combined balance fetcher with decryption
def get_balance(user_id: str, source: str, user: dict) -> dict:
    """
    Fetch balance for a user from the specified exchange.
    
    :param user_id: Unique user ID (string)
    :param source: 'luno' or 'binance'
    :param user: Dictionary containing ENCRYPTED API keys
    :return: Dictionary of balances
    """
    try:
        if source == "luno":
            decrypted_api_key = decrypt_data(user["luno_api_key"])
            decrypted_api_secret = decrypt_data(user["luno_api_secret"])
            print(f"[Debug] Decrypted Luno API key starts with: {decrypted_api_key[:5]}")
            return get_luno_balance(decrypted_api_key, decrypted_api_secret)

        elif source == "binance":
            decrypted_api_key = decrypt_data(user["binance_api_key"])
            decrypted_api_secret = decrypt_data(user["binance_api_secret"])
            print(f"[Debug] Decrypted Binance API key starts with: {decrypted_api_key[:5]}")
            return get_binance_balance(decrypted_api_key, decrypted_api_secret)

        else:
            print(f"[Error] Unknown exchange source: {source}")
            return {}

    except Exception as e:
        print(f"[Balance Fetch Error] Decryption or fetch error for {source}: {e}")
        return {}

# 🟩 Example usage
if __name__ == "__main__":
    # Example user data - Replace with actual DB values
    user_data = {
        "luno_api_key": "gAAAAABoR0RsQNF1dII4m_7Ibo8hm4hDPTQcD2c00Q8EBiyH1O-JkRXfsP3G8dK6RBkjAWe9SFUGl5fPSIaiR_KvTQjv25Ux1g==",
        "luno_api_secret": "gAAAAABoR0Rs1Yq4fb969mjYPOy_XgTbxYfu1zKLsH7Ujn0nxgxa6spymn2DDLN5xGCnHW6TpK8wkQLOUNFsYChbmhGq4Ip2nmz34Nz0Tr05a1mcOR8564qpxf2mfjG0Dof7zf6r2GI_",
        "binance_api_key": "gAAAAABoR0Rs...",
        "binance_api_secret": "gAAAAABoR0Rs...",
    }

    user_id = "user123"

    # Fetch balances
    luno_balances = get_balance(user_id, "luno", user_data)
    print("🔷 Luno Balances:", luno_balances)

    binance_balances = get_balance(user_id, "binance", user_data)
    print("🔷 Binance Balances:", binance_balances)
