import logging
from importlib import import_module
from firebase_admin import db
from notifications_manager import evaluate_and_notify_user

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def get_users_with_api_keys():
    """Fetch all users with API keys and strategy info from Firebase."""
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
                    "strategy": data.get("strategy", "arbitrage"),
                    "risk_tolerance": data.get("risk_tolerance", 0.02),
                    "profit_target": data.get("profit_target", 0.05),
                    "binance_api_key": data["binance_api_key"],
                    "binance_api_secret": data["binance_api_secret"],
                    "luno_api_key": data["luno_api_key"],
                    "luno_api_secret": data["luno_api_secret"],
                    "strategy_config": data.get("strategy_config", {}),
                    "notification_preferences": data.get("notification_preferences", {}),
                    "daily_profit": data.get("daily_profit", 0),
                    "last_trade_result": data.get("last_trade_result", None),
                    "strategy_score": data.get("strategy_score", 1.0),
                    "leaderboard_rank": data.get("leaderboard_rank", None),
                })

        return valid_users
    except Exception as e:
        logger.error(f"Error fetching users with API keys: {e}")
        return []

def run_auto_bot():
    """Run auto bot for all registered users with valid strategy and API keys."""
    users = get_users_with_api_keys()
    logger.info(f"Running auto bot for {len(users)} users")

    for user in users:
        logger.info(f"[{user['user_id']}] Running strategy '{user['strategy']}'")

        try:
            strategy_module = import_module(f"strategies.{user['strategy']}")
            strategy_module.execute(user)  # Strategy updates user’s profit/loss in Firebase
        except ModuleNotFoundError:
            logger.error(f"[{user['user_id']}] Strategy '{user['strategy']}' not found")
        except Exception as e:
            logger.error(f"[{user['user_id']}] Error executing strategy: {e}")

        try:
            evaluate_and_notify_user(user)  # Analyze and send alerts if needed
        except Exception as e:
            logger.error(f"[{user['user_id']}] Notifications error: {e}")

    logger.info("Auto bot cycle complete.")
