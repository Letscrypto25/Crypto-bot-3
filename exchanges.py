import base64
import os
import traceback
import requests
from firebase_admin import db
from binance.client import Client as BinanceClient
from cryptography.fernet import Fernet, InvalidToken

# === Fernet Setup with DEBUG ===
print("🔍 DEBUG: Starting Fernet secret load...")
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    print("❌ ERROR: SECRET_KEY is missing from environment.")
    raise RuntimeError("SECRET_KEY environment variable is not set")

print(f"🔍 DEBUG: SECRET_KEY (raw): {SECRET_KEY}")
print(f"🔍 DEBUG: Length of SECRET_KEY: {len(SECRET_KEY)}")

try:
    fernet = Fernet(SECRET_KEY.encode())
    print("✅ Fernet instance initialized successfully")
except Exception as e:
    print(f"❌ ERROR: Failed to initialize Fernet: {e}")
    raise

# === Decryption Function ===
def decrypt_api_key(encrypted_key: str) -> str:
    print(f"[DEBUG DECRYPT] Attempting to decrypt: {encrypted_key}")
    try:
        decrypted = fernet.decrypt(encrypted_key.encode()).decode()
        print(f"[DEBUG DECRYPT] Decrypted: {decrypted}")
        return decrypted
    except InvalidToken:
        print("❌ DEBUG: Invalid Fernet token - likely wrong SECRET_KEY or corrupted data")
        raise
    except Exception as e:
        print(f"❌ DEBUG: Decryption failed: {e}")
        raise

# === Binance ===
def get_binance_client(user_id, user=None):
    if user is None:
        user = db.reference(f"/users/{user_id}").get()
    encrypted_key = user.get("binance_api_key") or user.get("api_key")
    encrypted_secret = user.get("binance_api_secret") or user.get("api_secret")
    if not encrypted_key or not encrypted_secret:
        raise ValueError("Missing Binance API credentials.")
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
        traceback.print_exc()
        return None

# === Luno Auth Header (expects decrypted keys) ===
def get_luno_auth_header(api_key: str, api_secret: str) -> dict:
    print(f"[DEBUG AUTH] Using decrypted API key: {api_key[:4]}..., secret: {api_secret[:4]}...")
    auth = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
    return {"Authorization": f"Basic {auth}"}

# === Luno Price ===
def get_luno_price(user_id, pair="XBTZAR"):
    try:
        user = db.reference(f"/users/{user_id}").get()
        encrypted_key = user.get("luno_api_key") or user.get("api_key")
        encrypted_secret = user.get("luno_api_secret") or user.get("secret")

        api_key = decrypt_api_key(encrypted_key)
        api_secret = decrypt_api_key(encrypted_secret)

        headers = get_luno_auth_header(api_key, api_secret)

        url = f"https://api.luno.com/api/1/ticker?pair={pair}"
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return float(r.json()["last_trade"])
    except Exception as e:
        print(f"[Luno] Error fetching price for {pair}: {e}")
        traceback.print_exc()
        return None

# === Unified Price ===
def get_price(user_id, source="binance", symbol="BTCUSDT", pair="XBTZAR"):
    if source == "binance":
        return get_binance_price(user_id, symbol)
    elif source == "luno":
        return get_luno_price(user_id, pair)
    else:
        raise ValueError(f"Unknown exchange source: {source}")

# === Balance ===
def get_balance(user_id: str, source: str, user=None) -> dict:
    print(f"[Balance] Fetching for user {user_id} on {source}")
    try:
        if user is None:
            user = db.reference(f"/users/{user_id}").get()

        if source == "luno":
            enc_key = user.get("luno_api_key") or user.get("api_key")
            enc_secret = user.get("luno_api_secret") or user.get("secret")

            api_key = decrypt_api_key(enc_key)
            api_secret = decrypt_api_key(enc_secret)

            headers = get_luno_auth_header(api_key, api_secret)

            r = requests.get("https://api.luno.com/api/1/balance", headers=headers)
            print(f"[Luno Balance] Status Code: {r.status_code}")
            print(f"[Luno Balance] Response Body: {r.text}")
            r.raise_for_status()
            data = r.json().get("balance", [])
            return {
                asset["asset"]: float(asset["balance"])
                for asset in data
                if float(asset["balance"]) > 0
            }

        elif source == "binance":
            client = get_binance_client(user_id, user=user)
            raw_balances = client.get_account()["balances"]
            print("[Binance Balance] Raw:", raw_balances)
            return {
                b["asset"]: float(b["free"])
                for b in raw_balances
                if float(b["free"]) > 0
            }

        else:
            raise ValueError(f"Unknown exchange source: {source}")

    except Exception as e:
        print(f"[Balance Fetch Error] {e}")
        traceback.print_exc()
        return {}
