import time
import logging
from firebase_admin import db
from trading_api import trade_on_binance, trade_on_luno

logger = logging.getLogger(__name__)

def get_users_with_api_keys():
    """Fetch all users with API keys stored in Firebase."""
    try:
        users_ref = db.reference("/users")
        users_data = users_ref.get()
        if not users_data:
            return []

        valid_users = []
        for user_id, data in users_data.items():
            if "binance_api_key" in data and "luno_api_key" in data:
                valid_users.append({
                    "user_id": user_id,
                    "binance_api_key": data["binance_api_key"],
                    "binance_api_secret": data["binance_api_secret"],
                    "luno_api_key": data["luno_api_key"],
                    "luno_api_secret": data["luno_api_secret"],
                })

        return valid_users
    except Exception as e:
        logger.error(f"Error fetching users with API keys: {e}")
        return []

def run_auto_bot():
    """Run auto bot for all registered users with valid API keys."""
    users = get_users_with_api_keys()
    logger.info(f"Running auto bot for {len(users)} users")

    for user in users:
        logger.info(f"Running trades for user {user['user_id']}")
        try:
            binance_result = trade_on_binance(user)
            luno_result = trade_on_luno(user)
            logger.info(f"User {user['user_id']} Binance result: {binance_result}")
            logger.info(f"User {user['user_id']} Luno result: {luno_result}")
        except Exception as e:
            logger.error(f"Trade failed for user {user['user_id']}: {e}")

    logger.info("Auto bot cycle complete.")
