import os
import logging
import asyncio
import json
import tempfile
from datetime import datetime
from cryptography.fernet import Fernet
import firebase_admin
from firebase_admin import credentials, db
from quart import Quart, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from binance.client import Client
from luno_python.client import Client as LunoClient
from hypercorn.asyncio import serve
from hypercorn.config import Config

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Firebase
firebase_json = os.environ.get("FIREBASE_CREDENTIALS")
if not firebase_json:
    raise ValueError("FIREBASE_CREDENTIALS not set")
with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp:
    tmp.write(firebase_json)
    tmp.flush()
    cred = credentials.Certificate(tmp.name)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://crypto-bot-3-default-rtdb.firebaseio.com/'
    })

# Encryption
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY not set")
fernet = Fernet(SECRET_KEY)

# Quart
app = Quart(__name__)
telegram_app: Application = None

@app.route("/")
async def health():
    return "OK", 200

@app.route("/webhook/<token>", methods=["POST"])
async def telegram_webhook(token):
    if token != os.getenv("BOT_TOKEN"):
        return "Unauthorized", 403
    update_data = await request.get_json()
    update = Update.de_json(update_data, telegram_app.bot)
    await telegram_app.process_update(update)
    return "OK", 200

# Firebase helpers
def save_trade(uid, data):
    db.reference(f"trades/{uid}").push(data)

def save_error_to_firebase(message):
    ref = db.reference("errors")
    key = ref.push({
        "error": message,
        "timestamp": datetime.now().isoformat()
    })
    return key.key

def update_tournament(uid, profit_pct):
    ref = db.reference(f"tournaments/{uid}")
    stats = ref.get() or {}
    trades = stats.get("trades", 0) + 1
    avg_profit = (stats.get("profit_percent", 0) * stats.get("trades", 0) + profit_pct) / trades
    ref.set({
        "profit_percent": round(avg_profit, 2),
        "trades": trades,
        "last_updated": datetime.now().isoformat()
    })

# Telegram Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Crypto Bot! Use /help for options.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "/start - Welcome\n"
        "/help - List commands\n"
        "/setkeys <exchange> <key> <secret>\n"
        "/balance - Show balances\n"
        "/status - Show key status\n"
        "/deletekeys - Delete all keys\n"
        "/trades - Show trade history\n"
        "/tournament - Show tournament stats\n"
    )
    await update.message.reply_text(msg)

async def setkeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) != 3:
            raise ValueError("Usage: /setkeys <binance|luno> <api_key> <api_secret>")
        exchange, key, secret = context.args
        exchange = exchange.lower()
        if exchange not in ["binance", "luno"]:
            raise ValueError("Invalid exchange")

        encrypted = {
            f"{exchange}_api_key": fernet.encrypt(key.encode()).decode(),
            f"{exchange}_api_secret": fernet.encrypt(secret.encode()).decode()
        }
        uid = update.effective_user.id
        db.reference(f"api_keys/{uid}").update(encrypted)
        await update.message.reply_text(f"{exchange.title()} keys saved.")
    except Exception as e:
        err_id = save_error_to_firebase(str(e))
        await update.message.reply_text(f"Error: {e}. Logged: {err_id}")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    data = db.reference(f"api_keys/{uid}").get()
    if not data:
        await update.message.reply_text("Use /setkeys to save keys first.")
        return
    msg = ""
    try:
        if 'binance_api_key' in data:
            key = fernet.decrypt(data['binance_api_key'].encode()).decode()
            secret = fernet.decrypt(data['binance_api_secret'].encode()).decode()
            client = Client(key, secret)
            usdt = client.get_asset_balance(asset='USDT')
            msg += f"Binance USDT: {usdt['free']}\n"
    except Exception:
        msg += "Binance Error\n"
    try:
        if 'luno_api_key' in data:
            key = fernet.decrypt(data['luno_api_key'].encode()).decode()
            secret = fernet.decrypt(data['luno_api_secret'].encode()).decode()
            luno = LunoClient(key, secret)
            bal = luno.get_balances()["balance"]
            msg += "Luno:\n" + "\n".join(f"{b['asset']}: {b['balance']}" for b in bal)
    except Exception:
        msg += "Luno Error\n"
    await update.message.reply_text(msg or "No balances found.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    data = db.reference(f"api_keys/{uid}").get()
    if not data:
        await update.message.reply_text("No keys saved.")
        return
    await update.message.reply_text(
        f"Binance: {'Set' if data.get('binance_api_key') else 'Not Set'}\n"
        f"Luno: {'Set' if data.get('luno_api_key') else 'Not Set'}"
    )

async def deletekeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db.reference(f"api_keys/{uid}").delete()
    await update.message.reply_text("Keys deleted.")

async def trades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    trades = db.reference(f"trades/{uid}").get() or {}
    if not trades:
        await update.message.reply_text("No trades saved yet.")
        return
    lines = [
        f"{t.get('symbol')} - {t.get('side')} @ {t.get('price')}"
        for t in list(trades.values())[-5:]
    ]
    await update.message.reply_text("Recent Trades:\n" + "\n".join(lines))

async def tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    stats = db.reference(f"tournaments/{uid}").get()
    if not stats:
        await update.message.reply_text("You're not in the tournament yet.")
        return
    msg = (
        f"Profit %: {stats.get('profit_percent', '0')}\n"
        f"Trades: {stats.get('trades', '0')}\n"
        f"Updated: {stats.get('last_updated', '?')}"
    )
    await update.message.reply_text(msg)

# Boot Bot
async def main():
    global telegram_app
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN not set")

    telegram_app = Application.builder().token(token).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("setkeys", setkeys))
    telegram_app.add_handler(CommandHandler("balance", balance))
    telegram_app.add_handler(CommandHandler("status", status))
    telegram_app.add_handler(CommandHandler("deletekeys", deletekeys))
    telegram_app.add_handler(CommandHandler("trades", trades))
    telegram_app.add_handler(CommandHandler("tournament", tournament))

    await telegram_app.initialize()
    await telegram_app.start()

    base_url = os.getenv("BASE_URL", "https://crypto-bot-3-white-wind-424.fly.dev")
    await telegram_app.bot.set_webhook(f"{base_url}/webhook/{token}")
    logger.info(f"Webhook set to {base_url}/webhook/{token}")

    config = Config()
    config.bind = ["0.0.0.0:8080"]
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(main())
