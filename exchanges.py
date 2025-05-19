import requests
import os
import base64
from binance.client import Client

# --- BINANCE SETUP ---

def get_binance_client():
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        raise Exception("Binance API credentials not found in environment variables.")
    return Client(api_key, api_secret)

def get_binance_price(symbol="BTCUSDT"):
    try:
        client = get_binance_client()
        ticker = client.get_symbol_ticker(symbol=symbol)
        return float(ticker["price"])
    except Exception as e:
        print(f"Binance price fetch error: {e}")
        return None


# --- LUNO SETUP ---

def get_luno_auth():
    key = os.getenv("LUNO_API_KEY")
    secret = os.getenv("LUNO_API_SECRET")
    if not key or not secret:
        raise Exception("Luno API credentials not found in environment variables.")
    auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
    return {"Authorization": f"Basic {auth}"}

def get_luno_price(pair="XBTZAR"):
    try:
        url = f"https://api.luno.com/api/1/ticker?pair={pair}"
        headers = get_luno_auth()
        response = requests.get(url, headers=headers)
        data = response.json()
        return float(data["last_trade"])
    except Exception as e:
        print(f"Luno price fetch error: {e}")
        return None

# --- Example unified price function ---

def get_price(source="binance", symbol="BTCUSDT", pair="XBTZAR"):
    if source == "binance":
        return get_binance_price(symbol)
    elif source == "luno":
        return get_luno_price(pair)
    else:
        raise ValueError("Unknown exchange source.")
