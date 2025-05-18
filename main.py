from flask import Flask, request
from tasks import process_update_task
# Standard library
import os
import time
import base64
import logging
import threading
from datetime import datetime

# Third-party libraries
from flask import Flask, request
from celery import Celery
import redis
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db

# Telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

# Exchange clients
from binance.client import Client as BinanceClient

# Internal modules
from tasks import process_update_task

# === Logging Setup ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# === Environment Variables ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")
FIREBASE_CREDENTIALS_B64 = os.getenv("FIREBASE_CREDENTIALS")
BOT_TOKEN = TELEGRAM_BOT_TOKEN
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
if not FIREBASE_DATABASE_URL:
    raise ValueError("FIREBASE_DATABASE_URL environment variable not set")
if not FIREBASE_CREDENTIALS_B64:
    raise ValueError("FIREBASE_CREDENTIALS environment variable not set")

# === Firebase Initialization ===
try:
    if not firebase_admin._apps:
        firebase_json_str = base64.b64decode(FIREBASE_CREDENTIALS_B64).decode("utf-8")
        firebase_cred_path = "/tmp/firebase_credentials.json"
        with open(firebase_cred_path, "w", encoding="utf-8") as f:
            f.write(firebase_json_str)
        cred = credentials.Certificate(firebase_cred_path)
        firebase_admin.initialize_app(cred, {
            "databaseURL": FIREBASE_DATABASE_URL
        })
        logger.info("Firebase initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {e}")
    raise

redis_url = "redis://default:3fb87281db1b4ca38a98efad70b37e8e@fly-crypto-bot-redis.upstash.io:6379"
r = redis.from_url(redis_url)

# Optional: test connection
try:
    r.ping()
    print("Redis connected successfully.")
except redis.exceptions.ConnectionError as e:
    print("Redis connection failed:", e)

# === Firebase DB Reference ===
def get_user_ref(user_id):
    return db.reference(f"users/{user_id}")

def get_trades_ref(user_id):
    return db.reference(f"trades/{user_id}")

def get_leaderboard_ref():
    return db.reference("leaderboard")

# === Helper Functions for Firebase ===
def get_user_data(user_id):
    return get_user_ref(user_id).get() or {}

def update_user_data(user_id, data):
    get_user_ref(user_id).update(data)

def save_trade(user_id, trade_data):
    get_trades_ref(user_id).push(trade_data)

def update_leaderboard(user_id, profit):
    ref = get_leaderboard_ref()
    current = ref.get() or {}
    previous = current.get(str(user_id), 0)
    current[str(user_id)] = previous + profit
    ref.set(current)

# === Telegram Bot Initialization ===
telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
logger.info("Telegram bot initialized successfully")

# === Exchange Utilities ===

def get_binance_client(user_data):
    return BinanceClient(user_data['api_key'], user_data['api_secret'])

def get_luno_auth(user_data):
    return HTTPBasicAuth(user_data['api_key'], user_data['api_secret'])

# === Telegram Commands ===
def handle_update(update):
    print("Handling update:", update)
    # Your Telegram command parsing logic here
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Crypto Bot! Use /help for available commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Commands:\n"
        "/start - Welcome message\n"
        "/help - List of commands\n"
        "/register <exchange> <api_key> <api_secret> - Register your API keys\n"
        "/balance - Show your current balance\n"
        "/trade <BUY/SELL> <symbol> <amount> - Execute a trade\n"
        "/leaderboard - Show top traders\n"
        "/autobot enable|disable - Enable or disable auto trading\n"
        "/autobot config <key> <value> - Configure auto bot parameters\n"
    )
    await update.message.reply_text(help_text)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args

    if len(args) != 3:
        await update.message.reply_text("Usage: /register <binance/luno> <api_key> <api_secret>")
        return

    exchange, api_key, api_secret = args[0].lower(), args[1], args[2]
    if exchange not in ["binance", "luno"]:
        await update.message.reply_text("Exchange must be 'binance' or 'luno'")
        return

    update_user_data(user_id, {
        "exchange": exchange,
        "api_key": api_key,
        "api_secret": api_secret
    })

    await update.message.reply_text(f"Registered {exchange} API keys.")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if 'exchange' not in user_data:
        await update.message.reply_text("You're not registered. Use /register first.")
        return

    try:
        text = ""
        if user_data['exchange'] == 'binance':
            client = get_binance_client(user_data)
            acc = client.get_account()
            balances = [f"{b['asset']}: {b['free']}" for b in acc['balances'] if float(b['free']) > 0]
            text = "\n".join(balances) if balances else "No balances found."
        elif user_data['exchange'] == 'luno':
            resp = requests.get("https://api.luno.com/api/1/balance", auth=get_luno_auth(user_data)).json()
            balances = [f"{bal['asset']}: {bal['balance']}" for bal in resp['balance']]
            text = "\n".join(balances) if balances else "No balances found."
        else:
            text = "Exchange not recognized."

        await update.message.reply_text(text)
    except Exception as e:
        logger.exception("Balance fetch error")
        await update.message.reply_text(f"Error fetching balance: {e}")

async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if 'exchange' not in user_data:
        await update.message.reply_text("You're not registered. Use /register first.")
        return

    try:
        action, symbol, amount = context.args[0].upper(), context.args[1].upper(), float(context.args[2])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /trade <BUY/SELL> <SYMBOL> <AMOUNT>")
        return

    try:
        price = None
        if user_data['exchange'] == 'binance':
            client = get_binance_client(user_data)
            if action == "BUY":
                order = client.order_market_buy(symbol=symbol, quantity=amount)
            elif action == "SELL":
                order = client.order_market_sell(symbol=symbol, quantity=amount)
            else:
                await update.message.reply_text("Action must be BUY or SELL.")
                return
            price = order['fills'][0]['price']
        elif user_data['exchange'] == 'luno':
            market = symbol.lower()
            url = "https://api.luno.com/api/1/marketorder"
            side = "BUY" if action == "BUY" else "SELL"
            data = {"pair": market, "type": side.lower(), "counter_volume": str(amount)}
            resp = requests.post(url, auth=get_luno_auth(user_data), data=data)
            result = resp.json()
            if resp.status_code != 200:
                await update.message.reply_text(f"Luno API error: {result.get('error_message', resp.text)}")
                return
            price = result.get("average_price") or "unknown"
        else:
            await update.message.reply_text("Exchange not recognized.")
            return

        trade_record = {
            "symbol": symbol,
            "amount": amount,
            "side": action,
            "price": price,
            "timestamp": datetime.utcnow().isoformat()
        }
        save_trade(user_id, trade_record)

        await update.message.reply_text(f"{action} {amount} {symbol} at {price} — Executed")
    except Exception as e:
        logger.exception("Trade error")
        await update.message.reply_text(f"Trade failed: {e}")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ref = get_leaderboard_ref()
    data = ref.get() or {}
    if not data:
        await update.message.reply_text("Leaderboard is empty.")
        return

    top = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
    lines = [f"{i+1}. User {uid}: {profit:.2f}" for i, (uid, profit) in enumerate(top)]
    await update.message.reply_text("Leaderboard:\n" + "\n".join(lines))

# === Auto Bot Variables ===
AUTO_BOT_INTERVAL = 300  # seconds (5 minutes)
AUTO_BOT_ACTIVE = {}

# === Auto Bot Helper Functions ===

def get_latest_price(symbol, exchange, user_data):
    try:
        if exchange == "binance":
            client = get
            client = get_binance_client(user_data)
            ticker = client.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        elif exchange == "luno":
            url = f"https://api.luno.com/api/1/ticker?pair={symbol.lower()}"
            resp = requests.get(url)
            data = resp.json()
            return float(data["last_trade"])
        return None
    except Exception as e:
        logger.error(f"Price fetch error for {symbol}: {e}")
        return None

def autobot_loop():
    while True:
        all_users = db.reference("users").get() or {}
        for uid, data in all_users.items():
            uid = int(uid)
            if str(uid) in AUTO_BOT_ACTIVE and AUTO_BOT_ACTIVE[str(uid)]:
                try:
                    config = data.get("autobot_config", {})
                    symbol = config.get("symbol", "BTCUSDT")
                    max_spend = float(config.get("max_spend", 50))
                    tp = float(config.get("take_profit", 5))  # %
                    sl = float(config.get("stop_loss", 5))    # %

                    exchange = data.get("exchange")
                    price = get_latest_price(symbol, exchange, data)
                    if not price:
                        continue

                    # Simulate buy/sell logic based on thresholds
                    last_trade = get_trades_ref(uid).order_by_child("symbol").equal_to(symbol).limit_to_last(1).get()
                    if last_trade:
                        last_trade = list(last_trade.values())[0]
                        entry_price = float(last_trade.get("price", 0))
                        direction = last_trade.get("side")
                        if direction == "BUY":
                            gain = ((price - entry_price) / entry_price) * 100
                        else:
                            gain = ((entry_price - price) / entry_price) * 100

                        if gain >= tp:
                            update_leaderboard(uid, gain)
                            AUTO_BOT_ACTIVE[str(uid)] = False
                            send_telegram_message(uid, f"TP hit! Profit: {gain:.2f}% — Autobot paused.")
                        elif gain <= -sl:
                            update_leaderboard(uid, -sl)
                            AUTO_BOT_ACTIVE[str(uid)] = False
                            send_telegram_message(uid, f"SL hit! Loss: {gain:.2f}% — Autobot paused.")
                    else:
                        # Place dummy trade if none exists
                        dummy_trade = {
                            "symbol": symbol,
                            "amount": 0,
                            "side": "BUY",
                            "price": price,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        save_trade(uid, dummy_trade)
                        send_telegram_message(uid, f"Autobot placed dummy trade at {price}")

                except Exception as e:
                    logger.error(f"Autobot error for user {uid}: {e}")
        time.sleep(AUTO_BOT_INTERVAL)

def send_telegram_message(user_id, text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": user_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload)
    except Exception as e:
        logger.error(f"Failed to send Telegram message to {user_id}: {e}")

# === Autobot Commands ===

async def autobot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not context.args:
        await update.message.reply_text("Usage: /autobot enable|disable")
        return

    action = context.args[0].lower()
    if action == "enable":
        AUTO_BOT_ACTIVE[str(user_id)] = True
        await update.message.reply_text("Auto bot enabled.")
    elif action == "disable":
        AUTO_BOT_ACTIVE[str(user_id)] = False
        await update.message.reply_text("Auto bot disabled.")
    else:
        await update.message.reply_text("Invalid command. Use /autobot enable|disable")

async def autobot_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /autobot config <key> <value>")
        return

    key = context.args[0]
    value = context.args[1]
    user_data = get_user_data(user_id)
    config = user_data.get("autobot_config", {})
    config[key] = value
    update_user_data(user_id, {"autobot_config": config})
    await update.message.reply_text(f"Auto bot config updated: {key} = {value}")

# === Register Handlers ===
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("register", register))
telegram_app.add_handler(CommandHandler("balance", balance))
telegram_app.add_handler(CommandHandler("trade", trade))
telegram_app.add_handler(CommandHandler("leaderboard", leaderboard))
telegram_app.add_handler(CommandHandler("autobot", autobot))
telegram_app.add_handler(CommandHandler("autobot_config", autobot_config))

# === Start Threads ===
autobot_thread = threading.Thread(target=autobot_loop, daemon=True)
autobot_thread.start()

def make_celery(app_name=__name__):
    return Celery(
        app_name,
        broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        backend=os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )

celery_app = make_celery()
# === Run Bot ===
# === WEBHOOK ENDPOINT ===
WEBHOOK_PATH = "/webhook"  # Safer than exposing the token

app = Flask(__name__)

WEBHOOK_PATH = "/webhook"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update_json = request.get_json(force=True)
    process_update_task.delay(update_json)  # Send to Celery
    return "ok"

def set_webhook():
    webhook_url = f"https://{os.getenv('FLY_APP_NAME')}.fly.dev{WEBHOOK_PATH}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    res = requests.post(url, json={"url": webhook_url})
    print("Webhook set:", res.text)

if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

