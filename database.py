import os
import json
import firebase_admin
from firebase_admin import credentials, db
import logging

# Configure logging globally
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_firebase():
    """Initialize Firebase app directly from environment variable containing JSON credentials."""
    try:
        # Retrieve the Firebase credentials (already JSON, not encoded)
        creds_json = os.getenv("FIREBASE_CREDENTIALS_ENCODED")
        if not creds_json:
            raise ValueError("FIREBASE_CREDENTIALS_ENCODED is not set.")

        creds_dict = json.loads(creds_json)

        # Initialize the Firebase app
        if not firebase_admin._apps:
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred, {
                'databaseURL': os.getenv("FIREBASE_DATABASE_URL")
            })
            logger.info("Firebase app initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing Firebase: {e}")
        raise

# Initialize Firebase at import
initialize_firebase()

# === Firebase Database Reference ===
firebase_ref = db.reference("users")

# === User Management ===

def get_user(user_id):
    """Fetch user data by user_id."""
    try:
        return db.reference(f'users/{user_id}').get()
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return None

def get_all_users():
    """Fetch all users data."""
    try:
        return db.reference('users').get()
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return None

def create_user(user_id, default_data=None):
    """
    Create a new user with default data if not specified.
    """
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
        ref = db.reference(f'users/{user_id}')
        ref.set(default_data)
        logger.info(f"User {user_id} created with default data.")
    except Exception as e:
        logger.error(f"Error creating user {user_id}: {e}")

def update_user_data(user_id, data):
    """Update user data with a dictionary of fields."""
    try:
        db.reference(f'users/{user_id}').update(data)
        logger.info(f"User {user_id} data updated.")
    except Exception as e:
        logger.error(f"Error updating user {user_id} data: {e}")

def get_user_data(user_id):
    """Get all data for a user."""
    try:
        return db.reference(f'users/{user_id}').get()
    except Exception as e:
        logger.error(f"Error fetching data for user {user_id}: {e}")
        return None

# === Fetch users with all needed trading info for autobot ===
def get_users_with_api_keys_and_strategy():
    """
    Fetch users who have all required API keys and strategy info along with config parameters.
    Returns list of dicts with user info.
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

def set_balance(user_id, amount):
    """Set user balance to a specific amount."""
    try:
        db.reference(f'users/{user_id}/balance').set(amount)
        logger.info(f"Balance set to {amount} for user {user_id}.")
    except Exception as e:
        logger.error(f"Error setting balance for user {user_id}: {e}")

def get_balance(user_id):
    """Get user balance, returns 0 if not set."""
    try:
        return db.reference(f'users/{user_id}/balance').get() or 0
    except Exception as e:
        logger.error(f"Error getting balance for user {user_id}: {e}")
        return 0

# === Profit Tracking ===

def add_profit(user_id, profit):
    """
    Add profit to user profit atomically using Firebase transaction to avoid race conditions.
    """
    try:
        profit_ref = db.reference(f'users/{user_id}/profit')

        def transaction_update(current_profit):
            return (current_profit or 0) + profit

        profit_ref.transaction(transaction_update)
        logger.info(f"Added profit {profit} for user {user_id}.")
    except Exception as e:
        logger.error(f"Error adding profit for user {user_id}: {e}")

def get_profit(user_id):
    """Get total profit for user, defaults to 0."""
    try:
        return db.reference(f'users/{user_id}/profit').get() or 0
    except Exception as e:
        logger.error(f"Error getting profit for user {user_id}: {e}")
        return 0

# === Trade Data ===

def save_trade(user_id, trade_data):
    """Save a new trade record under trades/{user_id}."""
    try:
        db.reference(f'trades/{user_id}').push(trade_data)
        logger.info(f"Trade saved for user {user_id}.")
    except Exception as e:
        logger.error(f"Error saving trade for user {user_id}: {e}")

def get_user_trades(user_id):
    """Get all trades for a user, returns empty dict if none."""
    try:
        return db.reference(f'trades/{user_id}').get() or {}
    except Exception as e:
        logger.error(f"Error fetching trades for user {user_id}: {e}")
        return {}

# === Leaderboard ===

def update_leaderboard(user_id, profit):
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
    """Fetch leaderboard data or empty dict if none."""
    try:
        return db.reference('leaderboard').get() or {}
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        return {}

# === Autobot Config ===

def set_autobot_status(user_id, status: bool):
    try:
        db.reference(f'users/{user_id}/autobot/status').set(status)
        logger.info(f"Set autobot status {status} for user {user_id}.")
    except Exception as e:
        logger.error(f"Error setting autobot status for user {user_id}: {e}")

def get_autobot_status(user_id):
    try:
        return db.reference(f'users/{user_id}/autobot/status').get() or False
    except Exception as e:
        logger.error(f"Error getting autobot status for user {user_id}: {e}")
        return False

def set_autobot_platform(user_id, platform: str):
    try:
        db.reference(f'users/{user_id}/autobot/platform').set(platform)
        logger.info(f"Set autobot platform {platform} for user {user_id}.")
    except Exception as e:
        logger.error(f"Error setting autobot platform for user {user_id}: {e}")

def set_autobot_strategy(user_id, strategy: str):
    try:
        db.reference(f'users/{user_id}/autobot/strategy').set(strategy)
        logger.info(f"Set autobot strategy {strategy} for user {user_id}.")
    except Exception as e:
        logger.error(f"Error setting autobot strategy for user {user_id}: {e}")

def set_autobot_base(user_id, base: str):
    try:
        db.reference(f'users/{user_id}/autobot/base').set(base)
        logger.info(f"Set autobot base {base} for user {user_id}.")
    except Exception as e:
        logger.error(f"Error setting autobot base for user {user_id}: {e}")

def set_autobot_amount(user_id, amount: float):
    try:
        db.reference(f'users/{user_id}/autobot/amount').set(amount)
        logger.info(f"Set autobot amount {amount} for user {user_id}")
    except Exception as e:
        logger.error(f"Error setting autobot amount for user {user_id}: {e}")
