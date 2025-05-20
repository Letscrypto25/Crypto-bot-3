import os
import base64
import requests
from binance.client import Client as BinanceClient

# === Binance ===
def get_binance_client():
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        raise ValueError("Missing BINANCE_API_KEY or BINANCE_API_SECRET in environment.")
    return BinanceClient(api_key, api_secret)

def get_binance_price(symbol="BTCUSDT"):
    try:
        client = get_binance_client()
        ticker = client.get_symbol_ticker(symbol=symbol)
        return float(ticker["price"])
    except Exception as e:
        print(f"[Binance] Error fetching price for {symbol}: {e}")
        return None

# === Luno ===
def get_luno_auth_header():
    key = os.getenv("LUNO_API_KEY")
    secret = os.getenv("LUNO_API_SECRET")
    if not key or not secret:
        raise ValueError("Missing LUNO_API_KEY or LUNO_API_SECRET in environment.")
    auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
    return {"Authorization": f"Basic {auth}"}

def get_luno_price(pair="XBTZAR"):
    try:
        url = f"https://api.luno.com/api/1/ticker?pair={pair}"
        headers = get_luno_auth_header()
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return float(r.json()["last_trade"])
    except Exception as e:
        print(f"[Luno] Error fetching price for {pair}: {e}")
        return None

# === Unified Price Fetcher ===
def get_price(source="binance", symbol="BTCUSDT", pair="XBTZAR"):
    if source == "binance":
        return get_binance_price(symbol)
    elif source == "luno":
        return get_luno_price(pair)
    else:
        raise ValueError(f"Unknown exchange source: {source}")
