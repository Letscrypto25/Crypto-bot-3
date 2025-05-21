import logging
from firebase_admin import db
from importlib import import_module

logger = logging.getLogger(__name__)

def get_users_with_api_keys():
    try:
        users_ref = db.reference("/users")
        users_data = users_ref.get()
        if not users_data:
            return []

        valid_users = []
        for user_id, data in users_data.items():
            if "binance_api_key" in data and "luno_api_key" in data and "strategy" in data:
                valid_users.append({
                    "user_id": user_id,
                    "binance_api_key": data["binance_api_key"],
                    "binance_api_secret": data["binance_api_secret"],
                    "luno_api_key": data["luno_api_key"],
                    "luno_api_secret": data["luno_api_secret"],
                    "strategy": data["strategy"]
                })

        return valid_users
    except Exception as e:
        logger.error(f"Error fetching users with API keys: {e}")
        return []

def run_auto_bot():
    users = get_users_with_api_keys()
    logger.info(f"Running bot for {len(users)} users")

    for user in users:
        strategy_name = user.get("strategy", "spread_arbitrage").strip()
        logger.info(f"Running strategy '{strategy_name}' for user {user['user_id']}")
        try:
            strategy_module = import_module(f"strategies.{strategy_name}")
            result = strategy_module.run_strategy(user)
            logger.info(f"User {user['user_id']} result: {result}")
        except ModuleNotFoundError:
            logger.error(f"Strategy module '{strategy_name}' not found for user {user['user_id']}")
        except Exception as e:
            logger.error(f"Strategy failed for user {user['user_id']}: {e}")
