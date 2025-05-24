import os
import base64
import firebase_admin
from firebase_admin import credentials, db, initialize_app 
import logging

logger = logging.getLogger(__name__)

# Decode Firebase credentials if not already done
if not os.path.exists("firebase_credentials.json"):
    with open("firebase_encoded.txt", "r") as f:
        encoded = f.read().strip()
    decoded = base64.b64decode(encoded).decode("utf-8")
    with open("firebase_credentials.json", "w") as f:
        f.write(decoded)
# Initialize Firebase app if not initialized
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_credentials.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://crypto-bot-3-default-rtdb.firebaseio.com/'  # <-- Update if needed
    })

# === References ===
firebase_ref = db.reference("users")

# === User Management ===

def get_user(user_id):
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

def get_user_data(user_id):
    return db.reference(f'users/{user_id}').get()

# === Fetch users with all needed trading info for autobot ===
def get_users_with_api_keys_and_strategy():
    """Fetch users who have all API keys and strategy info along with config parameters."""
    try:
        users_data = get_all_users()
        if not users_data:
            return []

        valid_users = []
        for user_id, data in users_data.items():
            # Required API keys and strategy must exist
            if all(k in data for k in ("binance_api_key", "binance_api_secret", "luno_api_key", "luno_api_secret")) and "strategy" in data:
                # Prepare user's strategy config defaults if not present
                config = data.get("config", {})
                valid_users.append({
                    "user_id": user_id,
                    "strategy": data.get("strategy", "arbitrage"),
                    "risk_tolerance": data.get("risk_tolerance", 0.02),
                    "profit_target": data.get("profit_target", 50),
                    "dip_threshold": data.get("dip_threshold", -3.0),
                    "range_lower_bound": data.get("range_lower_bound", 29500),
                    "range_upper_bound": data.get("range_upper_bound", 30500),
                    "binance_api_key": data["binance_api_key"],
                    "binance_api_secret": data["binance_api_secret"],
                    "luno_api_key": data["luno_api_key"],
                    "luno_api_secret": data["luno_api_secret"],
                    "strategy_config": config.get("strategy_config", {}),
                    "notification_prefs": config.get("notifications", {
                        "telegram": True,
                        "push": True,
                        "email": False
                    }),
                    "autobot": data.get("autobot", {})
                })
        return valid_users

    except Exception as e:
        logger.error(f"Error fetching users with API keys and strategy: {e}")
        return []

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

# === User Config (strategy settings, notification prefs, etc) ===
def set_user_config(user_id, config: dict):
    db.reference(f'users/{user_id}/config').set(config)

def update_user_config(user_id, config_updates: dict):
    ref = db.reference(f'users/{user_id}/config')
    current_config = ref.get() or {}
    current_config.update(config_updates)
    ref.set(current_config)

def get_user_config(user_id):
    return db.reference(f'users/{user_id}/config').get() or {}

# === Notification Preferences ===
def set_notification_prefs(user_id, prefs: dict):
    """Example prefs: {'telegram': True, 'push': False, 'email': True}"""
    config = get_user_config(user_id)
    config['notifications'] = prefs
    set_user_config(user_id, config)

def get_notification_prefs(user_id):
    config = get_user_config(user_id)
    return config.get('notifications', {
        "telegram": True,
        "push": True,
        "email": False
    })

# === Trade Statistics / Tracking ===
def update_user_trade_stats(user_id, stats: dict):
    """
    Update trade stats for user, e.g. last_trade_time, last_profit, total_trades, etc.
    """
    try:
        user_ref = db.reference(f'users/{user_id}')
        user_ref.update(stats)
    except Exception as e:
        logger.error(f"Error updating trade stats for user {user_id}: {e}")

# === Cleanup / Reset ===
def delete_user(user_id):
    db.reference(f'users/{user_id}').delete()
    db.reference(f'trades/{user_id}').delete()
    db.reference(f'leaderboard/{user_id}').delete()

# === References used by commands or other modules ===
def get_leaderboard_ref():
    return db.reference("leaderboard")

def get_trades_ref():
    return db.reference("trades")
