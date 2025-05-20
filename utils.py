import json
import base64
import os
import requests
import firebase_admin
from firebase_admin import credentials, db
from binance.client import Client as BinanceClient
import time
import uuid
from datetime import datetime

# === Firebase Setup ===
def init_firebase():
    if not firebase_admin._apps:
        encoded = os.environ.get("FIREBASE_CREDENTIALS_ENCODED")
        db_url = os.environ.get("FIREBASE_DATABASE_URL")
        if not encoded or not db_url:
            raise ValueError("Missing Firebase credentials or database URL environment variables")
        try:
            decoded = base64.b64decode(encoded)
            creds_json = json.loads(decoded)
            cred = credentials.Certificate(creds_json)
            firebase_admin.initialize_app(cred, {'databaseURL': db_url})
            print("Firebase initialized successfully")
        except Exception as e:
            print(f"Error initializing Firebase: {e}")
            raise

init_firebase()

# === Telegram Messaging ===
TELEGRAM_API_URL = "https://api.telegram.org/bot"

def send_telegram_message(chat_id, text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN environment variable")
    url = f"{TELEGRAM_API_URL}{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Telegram send error: {e}")
        return False

# === Firebase User/Trade ===
USERS_PATH = "/users"
TRADES_PATH = "/trades"
LEADERBOARD_PATH = "/leaderboard"

def get_user_data(user_id):
    try:
        return db.reference(f"{USERS_PATH}/{user_id}").get() or {}
    except Exception as e:
        print(f"Error getting user data for {user_id}: {e}")
        return {}

def update_user_data(user_id, data):
    try:
        db.reference(f"{USERS_PATH}/{user_id}").update(data)
    except Exception as e:
        print(f"Error updating user data for {user_id}: {e}")

def get_trades_ref():
    return db.reference(TRADES_PATH)

def save_trade(user_id, trade_data):
    try:
        get_trades_ref().child(user_id).push(trade_data)
    except Exception as e:
        print(f"Error saving trade for {user_id}: {e}")

# === Binance ===
def get_binance_client(user_id):
    user = get_user_data(user_id)
    key = user.get("binance_api_key")
    secret = user.get("binance_api_secret")
    if not key or not secret:
        return None
    return BinanceClient(api_key=key, api_secret=secret)

# === Luno ===
def get_luno_auth(user_id):
    user = get_user_data(user_id)
    return user.get("luno_key"), user.get("luno_secret")

# === Leaderboard ===
def update_leaderboard(user_id, profit):
    try:
        ref = db.reference(f"{LEADERBOARD_PATH}/{user_id}")
        current = ref.get() or 0
        total = current + profit
        ref.set(round(total, 2))
    except Exception as e:
        print(f"Error updating leaderboard for {user_id}: {e}")

# === Price Helpers ===
def get_binance_price(symbol="BTCUSDT"):
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": symbol}, timeout=10)
        r.raise_for_status()
        return float(r.json()['price'])
    except Exception as e:
        print(f"Binance price error: {e}")
        return None

def get_luno_price(pair="XBTZAR"):
    try:
        r = requests.get(f"https://api.luno.com/api/1/ticker?pair={pair}", timeout=10)
        r.raise_for_status()
        return float(r.json()['last_trade'])
    except Exception as e:
        print(f"Luno price error: {e}")
        return None

# === Profit & Stats ===
def calculate_profit(entry, exit, amount, fees=0):
    try:
        return round((exit - entry) * amount - fees, 2)
    except Exception as e:
        print(f"Profit calculation error: {e}")
        return 0.0

def percentage_change(old, new):
    try:
        if old == 0:
            return 0.0
        return round(((new - old) / old) * 100, 2)
    except Exception as e:
        print(f"Percentage change error: {e}")
        return 0.0

# === Formatters ===
def format_trade_summary(trade):
    return (
        f"Trade: {trade.get('symbol', 'N/A')} | {trade.get('side', '').upper()}\n"
        f"Qty: {trade.get('amount', 'N/A')} at {trade.get('entry_price', 'N/A')}\n"
        f"Exit: {trade.get('exit_price', 'N/A')} | Profit: {trade.get('profit', 'N/A')}\n"
        f"Time: {trade.get('timestamp', 'N/A')}"
    )

def readable_timestamp(ts=None):
    try:
        return datetime.fromtimestamp(ts or time.time()).strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"Timestamp formatting error: {e}")
        return "N/A"

# === Helpers ===
def generate_id():
    return str(uuid.uuid4())[:8]

def safe_get(dct, key, default=None):
    return dct.get(key, default)

def is_float(value):
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False

# === Auth ===
def is_valid_user(user_id):
    return bool(get_user_data(user_id))
