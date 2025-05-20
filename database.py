import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, db

# Decode Firebase credentials
if not os.path.exists("firebase_credentials.json"):
    with open("firebase_encoded.txt", "r") as f:
        encoded = f.read().strip()
    decoded = base64.b64decode(encoded).decode("utf-8")
    with open("firebase_credentials.json", "w") as f:
        f.write(decoded)

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_credentials.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://crypto-bot-3-default-rtdb.firebaseio.com/'  # <-- Update if needed
    })

# === References ===
firebase_ref = db.reference("users")

# === User Management ===
def get_user_data(user_id):
    return db.reference(f'users/{user_id}').get()

def get_all_users():
    return db.reference('users').get()

def create_user(user_id, default_data=None):
    ref = db.reference(f'users/{user_id}')
    if default_data is None:
        default_data = {
            "balance": 0,
            "autobot": {
                "status": False,
                "platform": "binance",
                "strategy": "default",
                "base": "USDT",
                "amount": 0
            },
            "config": {},
            "profit": 0
        }
    ref.set(default_data)

def update_user_data(user_id, data):
    db.reference(f'users/{user_id}').update(data)

# === Balance ===
def set_balance(user_id, amount):
    db.reference(f'users/{user_id}/balance').set(amount)

def get_balance(user_id):
    return db.reference(f'users/{user_id}/balance').get() or 0

# === Profit Tracking ===
def add_profit(user_id, profit):
    profit_ref = db.reference(f'users/{user_id}/profit')
    current_profit = profit_ref.get() or 0
    profit_ref.set(current_profit + profit)

def get_profit(user_id):
    return db.reference(f'users/{user_id}/profit').get() or 0

# === Trade Data ===
def save_trade(user_id, trade_data):
    db.reference(f'trades/{user_id}').push(trade_data)

def get_user_trades(user_id):
    return db.reference(f'trades/{user_id}').get() or {}

# === Leaderboard ===
def update_leaderboard(user_id, profit):
    db.reference(f'leaderboard/{user_id}').set({
        'user_id': user_id,
        'profit': profit
    })

def get_leaderboard():
    return db.reference('leaderboard').get() or {}

# === Autobot Config ===
def set_autobot_status(user_id, status: bool):
    db.reference(f'users/{user_id}/autobot/status').set(status)

def get_autobot_status(user_id):
    return db.reference(f'users/{user_id}/autobot/status').get() or False

def set_autobot_platform(user_id, platform: str):
    db.reference(f'users/{user_id}/autobot/platform').set(platform)

def set_autobot_strategy(user_id, strategy: str):
    db.reference(f'users/{user_id}/autobot/strategy').set(strategy)

def set_autobot_base(user_id, base: str):
    db.reference(f'users/{user_id}/autobot/base').set(base)

def set_autobot_amount(user_id, amount: float):
    db.reference(f'users/{user_id}/autobot/amount').set(amount)

def get_autobot_config(user_id):
    return db.reference(f'users/{user_id}/autobot').get() or {}

# === Config ===
def set_user_config(user_id, config: dict):
    db.reference(f'users/{user_id}/config').set(config)

def get_user_config(user_id):
    return db.reference(f'users/{user_id}/config').get() or {}

# === Cleanup / Reset ===
def delete_user(user_id):
    db.reference(f'users/{user_id}').delete()
    db.reference(f'trades/{user_id}').delete()
    db.reference(f'leaderboard/{user_id}').delete()
