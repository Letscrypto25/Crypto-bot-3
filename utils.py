import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
USER_ID = os.getenv("TELEGRAM_USER_ID")
API_URL = os.getenv("TELEGRAM_API_URL")

def send_alert(message):
    try:
        url = f"{API_URL}/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": USER_ID, "text": message}
        requests.post(url, json=data)
    except Exception as e:
        print("Failed to send Telegram alert:", e)

def format_trade_message(direction, prices, rate):
    msg = f"Arbitrage: {direction}\n"
    msg += f"Luno Ask: {prices['luno_ask']}\n"
    msg += f"Luno Bid: {prices['luno_bid']}\n"
    msg += f"Binance Ask (ZAR): {round(prices['binance_ask'] * rate, 2)}\n"
    msg += f"Binance Bid (ZAR): {round(prices['binance_bid'] * rate, 2)}\n"
    msg += f"ZAR/USD Rate: {rate}"
    return msg
