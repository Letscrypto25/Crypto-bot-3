from celery_app import celery_app
from database import (
    get_all_users,
    get_autobot_status,
    get_autobot_config,
    get_balance,
    add_profit,
    save_trade,
    update_leaderboard
)
import requests
import random  # Simulated profit, replace with real trading logic

# Add your Telegram bot token (or import from settings)
BOT_TOKEN = "TELEGRAM_BOT_TOKEN"

def send_telegram_message(chat_id, text):
    """Send a message to a Telegram user."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Telegram send error: {e}")

@celery_app.task(name="tasks.run_auto_bot_task")
def run_auto_bot_task(payload=None):
    print("Running auto bot task...")

    users = get_all_users()
    if not users:
        return {"status": "no users found"}

    for user_id in users:
        try:
            status = get_autobot_status(user_id)
            if not status:
                continue

            config = get_autobot_config(user_id)
            amount = config.get("amount", 0)
            base = config.get("base", "USDT")

            if amount <= 0:
                continue

            # Simulate a trade result (replace this with real trade logic later)
            profit = round(random.uniform(-5, 10), 2)
            new_balance = get_balance(user_id) + profit

            # Update database
            add_profit(user_id, profit)
            update_leaderboard(user_id, new_balance)
            save_trade(user_id, {
                "profit": profit,
                "amount": amount,
                "base": base,
                "final_balance": new_balance
            })

            # Notify user
            send_telegram_message(user_id, f"AutoBot Trade: {profit} {base} | New Balance: {new_balance:.2f}")

        except Exception as e:
            print(f"Error processing user {user_id}: {str(e)}")

    return {"status": "completed"}
