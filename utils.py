import os
import requests
from cryptography.fernet import Fernet

# Constants
FERNET_KEY_PATH = "fernet.key"

# Telegram Configuration from environment
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
USER_ID = os.getenv("TELEGRAM_USER_ID")
API_URL = os.getenv("TELEGRAM_API_URL")

def load_or_generate_key():
    """Load Fernet key from file or generate a new one."""
    if os.path.exists(FERNET_KEY_PATH):
        with open(FERNET_KEY_PATH, "rb") as f:
            key = f.read()
    else:
        key = Fernet.generate_key()
        with open(FERNET_KEY_PATH, "wb") as f:
            f.write(key)
    return key

# Use environment key if set, else fallback to file key
FERNET_KEY = os.getenv("SECRET_KEY")
if FERNET_KEY:
    # SECRET_KEY from env is base64 encoded, ensure bytes
    if isinstance(FERNET_KEY, str):
        FERNET_KEY = FERNET_KEY.encode()
else:
    FERNET_KEY = load_or_generate_key()

fernet = Fernet(FERNET_KEY)

def encrypt(text: str) -> str:
    """Encrypt text using Fernet."""
    return fernet.encrypt(text.encode()).decode()

def decrypt(token: str) -> str:
    """Decrypt token using Fernet."""
    return fernet.decrypt(token.encode()).decode()

def send_alert(message: str, user_id: str = None) -> None:
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

def format_trade_message(direction: str, prices: dict, rate: float) -> str:
    """Build arbitrage trade summary."""
    return (
        f"*Arbitrage Opportunity: {direction}*\n\n"
        f"Luno Ask: R{prices['luno_ask']:.2f}\n"
        f"Luno Bid: R{prices['luno_bid']:.2f}\n"
        f"Binance Ask (ZAR): R{prices['binance_ask'] * rate:.2f}\n"
        f"Binance Bid (ZAR): R{prices['binance_bid'] * rate:.2f}\n"
        f"\nZAR/USD Rate: {rate:.2f}"
    )

def format_strategy_log(user: dict, strategy: str, action: str = None, details: str = None) -> str:
    """Format a summary log message for any strategy action."""
    msg = f"*Strategy:* {strategy}\n*User:* `{user['user_id']}`"
    if action:
        msg += f"\n*Action:* {action}"
    if details:
        msg += f"\n{details}"
    return msg
