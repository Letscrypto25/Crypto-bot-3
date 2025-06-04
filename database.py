import os
import json
import firebase_admin
from firebase_admin import credentials, db
import logging

# === Logging Setup ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_firebase():
    """Initialize Firebase app using JSON credentials from environment variable."""
    try:
        creds_json = os.getenv("FIREBASE_CREDENTIALS_ENCODED")
        if not creds_json:
            raise ValueError("FIREBASE_CREDENTIALS_ENCODED is not set.")
        creds_dict = json.loads(creds_json)
        if not firebase_admin._apps:
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred, {
                'databaseURL': os.getenv("FIREBASE_DATABASE_URL")
            })
            logger.info("Firebase app initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing Firebase: {e}")
        raise

# Initialize Firebase
initialize_firebase()

# === Database References ===
firebase_ref = db.reference("users")

# === User Management ===
def get_user(user_id: str):
    """Fetch a user’s data."""
    try:
        return db.reference(f'users/{user_id}').get()
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return None

def get_all_users():
    """Fetch all users."""
    try:
        return db.reference('users').get()
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return None

def create_user(user_id: str, default_data: dict = None):
    """Create a user with default data."""
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
    try:
        db.reference(f'users/{user_id}').set(default_data)
        logger.info(f"User {user_id} created with default data.")
    except Exception as e:
        logger.error(f"Error creating user {user_id}: {e}")

def update_user_data(user_id: str, data: dict):
    """Update user data."""
    try:
        db.reference(f'users/{user_id}').update(data)
        logger.info(f"User {user_id} data updated.")
    except Exception as e:
        logger.error(f"Error updating user {user_id} data: {e}")

def get_user_data(user_id: str):
    """Get user data."""
    try:
        return db.reference(f'users/{user_id}').get()
    except Exception as e:
        logger.error(f"Error getting data for user {user_id}: {e}")
        return None

def get_users_with_api_keys_and_strategy():
    """
    Fetch users who have API keys and trading strategy info.
    """
    try:
        users_data = get_all_users()
        if not users_data:
            return []

        valid_users = []
        for user_id, data in users_data.items():
            if all(k in data for k in ("binance_api_key", "binance_api_secret", "luno_api_key", "luno_api_secret")) and "strategy" in data:
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
def set_balance(user_id: str, amount: float):
    """Set balance for a user."""
    try:
        db.reference(f'users/{user_id}/balance').set(amount)
        logger.info(f"Balance set to {amount} for user {user_id}.")
    except Exception as e:
        logger.error(f"Error setting balance for user {user_id}: {e}")

def get_balance(user_id: str) -> float:
    """Get user balance, default 0."""
    try:
        return db.reference(f'users/{user_id}/balance').get() or 0
    except Exception as e:
        logger.error(f"Error getting balance for user {user_id}: {e}")
        return 0

# === Profit Tracking ===
def add_profit(user_id: str, profit: float):
    """Add profit to user’s record using transaction for atomic update."""
    try:
        profit_ref = db.reference(f'users/{user_id}/profit')

        def transaction_update(current_profit):
            return (current_profit or 0) + profit

        profit_ref.transaction(transaction_update)
        logger.info(f"Added profit {profit} for user {user_id}.")
    except Exception as e:
        logger.error(f"Error adding profit for user {user_id}: {e}")

def get_profit(user_id: str) -> float:
    """Get total profit, default 0."""
    try:
        return db.reference(f'users/{user_id}/profit').get() or 0
    except Exception as e:
        logger.error(f"Error getting profit for user {user_id}: {e}")
        return 0

# === Trades ===
def save_trade(user_id: str, trade_data: dict):
    """Save a trade record."""
    try:
        db.reference(f'trades/{user_id}').push(trade_data)
        logger.info(f"Trade saved for user {user_id}.")
    except Exception as e:
        logger.error(f"Error saving trade for user {user_id}: {e}")

def get_user_trades(user_id: str):
    """Get all trades for a user."""
    try:
        return db.reference(f'trades/{user_id}').get() or {}
    except Exception as e:
        logger.error(f"Error getting trades for user {user_id}: {e}")
        return {}

# === Leaderboard ===
def update_leaderboard(user_id: str, profit: float):
    """Update leaderboard entry for a user."""
    try:
        db.reference(f'leaderboard/{user_id}').set({
            'user_id': user_id,
            'profit': profit
        })
        logger.info(f"Leaderboard updated for user {user_id} with profit {profit}.")
    except Exception as e:
        logger.error(f"Error updating leaderboard for user {user_id}: {e}")

def get_leaderboard():
    """Get leaderboard data."""
    try:
        return db.reference('leaderboard').get() or {}
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        return {}

# === Autobot Settings ===
def set_autobot_status(user_id: str, status: bool):
    """Set autobot status."""
    try:
        db.reference(f'users/{user_id}/autobot/status').set(status)
        logger.info(f"Set autobot status {status} for user {user_id}.")
    except Exception as e:
        logger.error(f"Error setting autobot status for user {user_id}: {e}")

def get_autobot_status(user_id: str) -> bool:
    """Get autobot status."""
    try:
        return db.reference(f'users/{user_id}/autobot/status').get() or False
    except Exception as e:
        logger.error(f"Error getting autobot status for user {user_id}: {e}")
        return False

def set_autobot_platform(user_id: str, platform: str):
    """Set autobot trading platform."""
    try:
        db.reference(f'users/{user_id}/autobot/platform').set(platform)
        logger.info(f"Set autobot platform {platform} for user {user_id}.")
    except Exception as e:
        logger.error(f"Error setting autobot platform for user {user_id}: {e}")

def set_autobot_strategy(user_id: str, strategy: str):
    """Set autobot strategy."""
    try:
        db.reference(f'users/{user_id}/autobot/strategy').set(strategy)
        logger.info(f"Set autobot strategy {strategy} for user {user_id}.")
    except Exception as e:
        logger.error(f"Error setting autobot strategy for user {user_id}: {e}")

def set_autobot_base(user_id: str, base: str):
    """Set autobot trading base currency."""
    try:
        db.reference(f'users/{user_id}/autobot/base').set(base)
        logger.info(f"Set autobot base {base} for user {user_id}.")
    except Exception as e:
        logger.error(f"Error setting autobot base for user {user_id}: {e}")

def set_autobot_amount(user_id: str, amount: float):
    """Set autobot trade amount."""
    try:
        db.reference(f'users/{user_id}/autobot/amount').set(amount)
        logger.info(f"Set autobot amount {amount} for user {user_id}.")
    except Exception as e:
        logger.error(f"Error setting autobot amount for user {user_id}: {e}")
