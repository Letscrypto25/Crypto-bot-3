import base64
import requests
from firebase_admin import db
from binance.client import Client as BinanceClient
from cryptography.fernet import Fernet
import os

# === Fernet Setup ===
SECRET_KEY = os.getenv("SECRET_KEY")  # e.g. "nSGfGz_aOcK9i3S6cvlB3mDiSfqNyCwJ_fZ1L6bXb1o="
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set")
fernet = Fernet(SECRET_KEY.encode())

def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt encrypted API keys stored in Firebase."""
    return fernet.decrypt(encrypted_key.encode()).decode()

# === Binance ===
def get_binance_client(user_id):
    user_data = db.reference(f"/users/{user_id}").get()
    api_key = user_data.get("binance_api_key")
    api_secret = user_data.get("binance_api_secret")
    if not api_key or not api_secret:
        raise ValueError("Missing Binance API credentials for user.")
    return BinanceClient(api_key, api_secret)

def get_binance_price(user_id, symbol="BTCUSDT"):
    try:
        client = get_binance_client(user_id)
        ticker = client.get_symbol_ticker(symbol=symbol)
        return float(ticker["price"])
    except Exception as e:
        print(f"[Binance] Error fetching price for {symbol}: {e}")
        return None

# === Luno ===
def get_luno_auth_header(user_id):
    user_data = db.reference(f"/users/{user_id}").get()
    encrypted_key = user_data.get("api_key")   # Encrypted key from Firebase
    encrypted_secret = user_data.get("secret") # Encrypted secret from Firebase
    if not encrypted_key or not encrypted_secret:
        raise ValueError("Missing Luno API credentials for user.")
    # Decrypt keys before use
    key = decrypt_api_key(encrypted_key)
    secret = decrypt_api_key(encrypted_secret)
    auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
    return {"Authorization": f"Basic {auth}"}
    
def get_luno_price(user_id, pair="XBTZAR"):
    try:
        url = f"https://api.luno.com/api/1/ticker?pair={pair}"
        headers = get_luno_auth_header(user_id)
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return float(r.json()["last_trade"])
    except Exception as e:
        print(f"[Luno] Error fetching price for {pair}: {e}")
        return None

# === Unified Price Fetcher ===
def get_price(user_id, source="binance", symbol="BTCUSDT", pair="XBTZAR"):
    if source == "binance":
        return get_binance_price(user_id, symbol)
    elif source == "luno":
        return get_luno_price(user_id, pair)
    else:
        raise ValueError(f"Unknown exchange source: {source}")

def get_balance(user_id: str, source: str, user=None) -> dict:
    print(f"Fetching balance for user: {user_id} on {source}")
    try:
        if source == "luno":
            # Decrypt keys if user dict not passed
            if user is None:
                user_data = db.reference(f"/users/{user_id}").get()
                encrypted_key = user_data.get("api_key")
                encrypted_secret = user_data.get("secret")
                if not encrypted_key or not encrypted_secret:
                    raise ValueError("Missing Luno API credentials for user.")
                key = decrypt_api_key(encrypted_key)
                secret = decrypt_api_key(encrypted_secret)
            else:
                key = user["api_key"]
                secret = user["secret"]
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
            client = get_binance_client(user_id)
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
        print(f"[Balance Fetch Error] {e}")
        return {}
