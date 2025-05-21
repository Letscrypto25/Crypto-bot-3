import base64
import requests
from binance.client import Client as BinanceClient
from database import get_user_config  # assumes you have this working

# === Binance ===
def get_binance_client(user_id):
    config = get_user_config(user_id)
    api_key = config.get("binance_key")
    api_secret = config.get("binance_secret")
    if not api_key or not api_secret:
        raise ValueError(f"Missing Binance credentials for user {user_id}")
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
def get_luno_auth(user_id):
    config = get_user_config(user_id)
    key = config.get("luno_key")
    secret = config.get("luno_secret")
    if not key or not secret:
        raise ValueError(f"Missing Luno credentials for user {user_id}")
    auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
    return {"Authorization": f"Basic {auth}"}

def get_luno_price(user_id, pair="XBTZAR"):
    try:
        url = f"https://api.luno.com/api/1/ticker?pair={pair}"
        headers = get_luno_auth(user_id)
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
