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
    try:
        return db.reference(f'users/{user_id}').get()
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return None

def get_all_users():
    try:
        return firebase_ref.get()
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return None

def create_user(user_id: str, default_data: dict = None):
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
            "config": {
                "binance_api_key": "",
                "binance_api_secret": "",
                "luno_api_key": "",
                "luno_api_secret": "",
                "strategy_config": {},
                "notifications": {
                    "telegram": True,
                    "push": True,
                    "email": False
                }
            },
            "profit": 0
        }
    try:
        db.reference(f'users/{user_id}').set(default_data)
        logger.info(f"User {user_id} created with default data.")
    except Exception as e:
        logger.error(f"Error creating user {user_id}: {e}")

def update_user_data(user_id: str, data: dict):
    try:
        db.reference(f'users/{user_id}').update(data)
        logger.info(f"User {user_id} data updated.")
    except Exception as e:
        logger.error(f"Error updating user {user_id} data: {e}")

# === API Keys Handling in Config ===
def set_api_keys(user_id: str, binance_api_key: str, binance_api_secret: str, luno_api_key: str, luno_api_secret: str):
    """Store user API keys inside config section."""
    try:
        config_ref = db.reference(f'users/{user_id}/config')
        config_ref.update({
            "binance_api_key": binance_api_key,
            "binance_api_secret": binance_api_secret,
            "luno_api_key": luno_api_key,
            "luno_api_secret": luno_api_secret
        })
        logger.info(f"API keys updated for user {user_id}.")
    except Exception as e:
        logger.error(f"Error setting API keys for user {user_id}: {e}")

def get_api_keys(user_id: str):
    """Retrieve API keys from config section."""
    try:
        config = db.reference(f'users/{user_id}/config').get() or {}
        return {
            "binance_api_key": config.get("binance_api_key", ""),
            "binance_api_secret": config.get("binance_api_secret", ""),
            "luno_api_key": config.get("luno_api_key", ""),
            "luno_api_secret": config.get("luno_api_secret", "")
        }
    except Exception as e:
        logger.error(f"Error getting API keys for user {user_id}: {e}")
        return {}

# === Fetch Users with API keys and Strategy ===
def get_users_with_api_keys_and_strategy():
    try:
        users_data = get_all_users()
        if not users_data:
            return []

        valid_users = []
        for user_id, data in users_data.items():
            config = data.get("config", {})
            autobot = data.get("autobot", {})
            # Check if all API keys are present
            if all(config.get(k) for k in ("binance_api_key", "binance_api_secret", "luno_api_key", "luno_api_secret")):
                valid_users.append({
                    "user_id": user_id,
                    "strategy": autobot.get("strategy", "default"),
                    "risk_tolerance": data.get("risk_tolerance", 0.02),
                    "profit_target": data.get("profit_target", 50),
                    "dip_threshold": data.get("dip_threshold", -3.0),
                    "range_lower_bound": data.get("range_lower_bound", 29500),
                    "range_upper_bound": data.get("range_upper_bound", 30500),
                    "binance_api_key": config.get("binance_api_key"),
                    "binance_api_secret": config.get("binance_api_secret"),
                    "luno_api_key": config.get("luno_api_key"),
                    "luno_api_secret": config.get("luno_api_secret"),
                    "strategy_config": config.get("strategy_config", {}),
                    "notification_prefs": config.get("notifications", {
                        "telegram": True,
                        "push": True,
                        "email": False
                    }),
                    "autobot": autobot
                })
        return valid_users

    except Exception as e:
        logger.error(f"Error fetching users with API keys and strategy: {e}")
        return []

# === Get autobot status for a user ===
def get_autobot_status(user_id: str) -> bool:
    """
    Retrieve the autobot status (True/False) for a given user.
    """
    try:
        status = db.reference(f'users/{user_id}/autobot/status').get()
        if status is None:
            return False
        return bool(status)
    except Exception as e:
        logger.error(f"Error getting autobot status for user {user_id}: {e}")
        return False
