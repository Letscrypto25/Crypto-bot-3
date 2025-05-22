import os
import requests
from datetime import datetime
import firebase_admin
from firebase_admin import db

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
USER_ID = os.getenv("TELEGRAM_USER_ID")
API_URL = os.getenv("TELEGRAM_API_URL")


def send_alert(message, user_id=None):
    """Send Telegram alert to a specific user (or default)."""
    try:
        url = f"{API_URL}/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": user_id or USER_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=data)
    except Exception as e:
        print("Failed to send Telegram alert:", e)


def format_trade_message(direction, prices, rate):
    """Build arbitrage trade summary."""
    return (
        f"*Arbitrage Opportunity: {direction}*\n\n"
        f"Luno Ask: R{prices['luno_ask']:.2f}\n"
        f"Luno Bid: R{prices['luno_bid']:.2f}\n"
        f"Binance Ask (ZAR): R{prices['binance_ask'] * rate:.2f}\n"
        f"Binance Bid (ZAR): R{prices['binance_bid'] * rate:.2f}\n"
        f"\nZAR/USD Rate: {rate:.2f}"
    )


def format_strategy_log(user, strategy, action=None, details=None):
    """Format a summary log message for any strategy action."""
    msg = f"*Strategy:* {strategy}\n*User:* `{user['user_id']}`"
    if action:
        msg += f"\n*Action:* {action}"
    if details:
        msg += f"\n{details}"
    return msg


def log_event(user_id, event_type, message_text, status="ok", error=None):
    """Log user event to Firebase Realtime DB under /logs/{user_id}/."""
    try:
        if not firebase_admin._apps:
            return  # Firebase should already be initialized elsewhere

        log_ref = db.reference(f"logs/{user_id}")
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event_type,
            "message": message_text,
            "status": status,
        }
        if error:
            log_entry["error"] = str(error)
        log_ref.push(log_entry)
    except Exception as e:
        print("Logging error:", e)
