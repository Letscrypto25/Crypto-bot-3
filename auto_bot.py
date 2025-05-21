import logging
from firebase_admin import db
from strategies.spread_arbitrage import run_strategy  # import your strategy

logger = logging.getLogger(__name__)

def get_users_with_api_keys():
    # your original Firebase logic
    ...

def run_auto_bot():
    users = get_users_with_api_keys()
    logger.info(f"Running strategy for {len(users)} users")

    for user in users:
        try:
            logger.info(f"Running strategy for user {user['user_id']}")
            result = run_strategy(user)  # Use selected strategy
            logger.info(f"User {user['user_id']} result: {result}")
        except Exception as e:
            logger.error(f"Strategy failed for user {user['user_id']}: {e}")
