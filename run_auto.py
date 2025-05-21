import os import time from firebase import FirebaseManager from luno_binance import LunoClient, BinanceClient from utils import send_telegram_message, calculate_profit_margin, log_trade

Load environment variables

TELEGRAM_USER_ID = os.environ.get("TELEGRAM_USER_ID") FIREBASE_DATABASE_URL = os.environ.get("FIREBASE_DATABASE_URL") FIREBASE_CREDENTIALS_ENCODED = os.environ.get("FIREBASE_CREDENTIALS_ENCODED")

Init Firebase

firebase = FirebaseManager(FIREBASE_CREDENTIALS_ENCODED, FIREBASE_DATABASE_URL)

Init clients

luno_client = LunoClient(firebase) binance_client = BinanceClient(firebase)

Parameters (can be set per user via Firebase in future)

MIN_PROFIT_MARGIN = 0.5  # Minimum % profit to trade TRADE_AMOUNT = 100       # Amount to trade in USD equivalent

def auto_trade(): # Example: BTC/USDT pair try: luno_price = luno_client.get_price("BTC/USDT") binance_price = binance_client.get_price("BTC/USDT")

profit_margin = calculate_profit_margin(luno_price, binance_price)

    if profit_margin >= MIN_PROFIT_MARGIN:
        # Determine direction
        if binance_price > luno_price:
            buy_exchange = "Luno"
            sell_exchange = "Binance"
            buy_client = luno_client
            sell_client = binance_client
        else:
            buy_exchange = "Binance"
            sell_exchange = "Luno"
            buy_client = binance_client
            sell_client = luno_client

        # Place trades
        buy_order = buy_client.place_order("BTC/USDT", TRADE_AMOUNT, side="buy")
        sell_order = sell_client.place_order("BTC/USDT", TRADE_AMOUNT, side="sell")

        # Log and notify
        trade_data = {
            "pair": "BTC/USDT",
            "buy_exchange": buy_exchange,
            "sell_exchange": sell_exchange,
            "buy_price": buy_order.get("price"),
            "sell_price": sell_order.get("price"),
            "profit_margin": profit_margin,
            "timestamp": time.time(),
        }

        firebase.log_trade(trade_data)
        log_trade(trade_data)

        send_telegram_message(
            f"Auto trade executed:\nBuy on {buy_exchange} at {buy_order.get('price')}\n"
            f"Sell on {sell_exchange} at {sell_order.get('price')}\n"
            f"Profit Margin: {profit_margin:.2f}%"
        )

    else:
        send_telegram_message(f"No profitable opportunity. Margin: {profit_margin:.2f}%")

except Exception as e:
    send_telegram_message(f"Auto bot error: {str(e)}")
    print(f"Error: {str(e)}")

if name == "main": while True: auto_trade() time.sleep(30)  # Run every 30 seconds


