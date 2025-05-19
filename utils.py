import json
import base64
import requests
import firebase_admin
from firebase_admin import credentials, db
from binance.client import Client as BinanceClient

FIREBASE_CREDENTIALS_ENCODED = "fb64.txt"
TELEGRAM_API_URL = "https://api.telegram.org/bot"
LEADERBOARD_PATH = "/leaderboard"
TRADES_PATH = "/trades"
USERS_PATH = "/users"

# === Firebase Setup ===
def init_firebase():
    if not firebase_admin._apps:
        with open(FIREBASE_CRED_FILE, "r") as f:
            encoded = f.read()
        decoded = base64.b64decode(encoded)
        cred = credentials.Certificate(json.loads(decoded))
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'FIREBASE_DATABASE_URL'
        })

init_firebase()

# === Telegram Messaging ===
def send_telegram_message(chat_id, text):
    token = get_bot_token()
    url = f"{TELEGRAM_API_URL}{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        response = requests.post(url, json=payload)
        return response.ok
    except Exception as e:
        print(f"Telegram send error: {e}")
        return False

def get_bot_token():
    # Load from env or store as plain text for now
    with open("bot_token.txt") as f:
        return f.read().strip()

# === Firebase User/Trade ===
def get_user_data(user_id):
    ref = db.reference(f"{USERS_PATH}/{user_id}")
    return ref.get() or {}

def update_user_data(user_id, data):
    ref = db.reference(f"{USERS_PATH}/{user_id}")
    ref.update(data)

def get_trades_ref():
    return db.reference(TRADES_PATH)

def save_trade(user_id, trade_data):
    ref = get_trades_ref().child(user_id)
    ref.push(trade_data)

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
    ref = db.reference(LEADERBOARD_PATH).child(user_id)
    current = ref.get()
    total = (current or 0) + profit
    ref.set(round(total, 2))

import time
import uuid
from datetime import datetime

# === Price Helpers ===
def get_binance_price(symbol="BTCUSDT"):
    try:
        response = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": symbol})
        data = response.json()
        return float(data['price'])
    except Exception as e:
        print(f"Price fetch error: {e}")
        return None

def get_luno_price(pair="XBTZAR"):
    try:
        response = requests.get(f"https://api.luno.com/api/1/ticker?pair={pair}")
        data = response.json()
        return float(data['last_trade'])
    except Exception as e:
        print(f"Luno price fetch error: {e}")
        return None

# === Profit & Stats ===
def calculate_profit(entry, exit, amount, fees=0):
    gross = (exit - entry) * amount
    net = gross - fees
    return round(net, 2)

def percentage_change(old, new):
    try:
        return round(((new - old) / old) * 100, 2)
    except ZeroDivisionError:
        return 0.0

# === Formatters ===
def format_trade_summary(trade):
    return (
        f"Trade: {trade['symbol']} | {trade['side'].upper()}\n"
        f"Qty: {trade['amount']} at {trade['entry_price']}\n"
        f"Exit: {trade['exit_price']} | Profit: {trade['profit']}\n"
        f"Time: {trade.get('timestamp', 'N/A')}"
    )

def readable_timestamp(ts=None):
    return datetime.fromtimestamp(ts or time.time()).strftime("%Y-%m-%d %H:%M:%S")

# === Helpers ===
def generate_id():
    return str(uuid.uuid4())[:8]

def safe_get(dct, key, default=None):
    return dct.get(key, default)

def is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


