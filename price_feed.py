import base64
import requests
from firebase_admin import db
from binance.client import Client as BinanceClient
from cryptography.fernet import Fernet
import os

# === Fernet Setup ===
SECRET_KEY = os.getenv("SECRET_KEY")  # Must be securely stored
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set")
fernet = Fernet(SECRET_KEY.encode())

def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt encrypted API keys stored in Firebase."""
    return fernet.decrypt(encrypted_key.encode()).decode()

# === Binance ===
def get_binance_client(user_id, user=None):
    if user is None:
        user = db.reference(f"/users/{user_id}").get()

    encrypted_key = user.get("binance_api_key") or user.get("api_key")
    encrypted_secret = user.get("binance_api_secret") or user.get("api_secret")

    if not encrypted_key or not encrypted_secret:
        raise ValueError("Missing Binance API credentials for user.")

    api_key = decrypt_api_key(encrypted_key)
    api_secret = decrypt_api_key(encrypted_secret)
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
def get_luno_auth_header(user_id=None, user=None):
    if user is None:
        if not user_id:
            raise ValueError("Must provide user_id or user data")
        user = db.reference(f"/users/{user_id}").get()

    encrypted_key = user.get("luno_api_key") or user.get("api_key")
    encrypted_secret = user.get("luno_api_secret") or user.get("secret")

    if not encrypted_key or not encrypted_secret:
        raise ValueError("Missing Luno API credentials.")

    key = decrypt_api_key(encrypted_key)
    secret = decrypt_api_key(encrypted_secret)
    auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
    return {"Authorization": f"Basic {auth}"}

def get_luno_price(user_id, pair="XBTZAR"):
    try:
        headers = get_luno_auth_header(user_id=user_id)
        url = f"https://api.luno.com/api/1/ticker?pair={pair}"
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return float(r.json()["last_trade"])
    except Exception as e:
        print(f"[Luno] Error fetching price for {pair}: {e}")
        return None

# === Unified Price ===
def get_price(user_id, source="binance", symbol="BTCUSDT", pair="XBTZAR"):
    if source == "binance":
        return get_binance_price(user_id, symbol)
    elif source == "luno":
        return get_luno_price(user_id, pair)
    else:
        raise ValueError(f"Unknown exchange source: {source}")
