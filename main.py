import os import json import asyncio import logging import tempfile from datetime import datetime

import firebase_admin from firebase_admin import credentials, db from quart import Quart, request from telegram import Update from telegram.ext import Application, CommandHandler, ContextTypes from binance.client import Client as BinanceClient from luno_python.client import Client as LunoClient from cryptography.fernet import Fernet from hypercorn.asyncio import serve from hypercorn.config import Config

Setup logging

logging.basicConfig(level=logging.INFO) logger = logging.getLogger(name)

Firebase setup

firebase_json = os.environ.get("FIREBASE_CREDENTIALS") if not firebase_json: raise ValueError("FIREBASE_CREDENTIALS not set")

with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp: tmp.write(firebase_json) tmp.flush() cred = credentials.Certificate(tmp.name) firebase_admin.initialize_app(cred, { 'databaseURL': 'https://crypto-bot-3-default-rtdb.firebaseio.com/' })

Encryption key setup

secret_key = os.getenv("SECRET_KEY") if not secret_key: raise ValueError("SECRET_KEY not set") fernet = Fernet(secret_key.encode())

Quart app

app = Quart(name) telegram_app: Application = None initialized = False

@app.route("/") async def health(): return "OK", 200

@app.route("/webhook/<token>", methods=["POST"]) async def telegram_webhook(token): global telegram_app, initialized if token != os.getenv("BOT_TOKEN"): return "Unauthorized", 403

if not initialized:
    await telegram_app.initialize()
    initialized = True

update_data = await request.get_json()
update = Update.de_json(update_data, telegram_app.bot)
await telegram_app.process_update(update)
return "OK", 200

--- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("Welcome to the Crypto Trading Bot! Use /setkeys <source> <key> <secret> to set your API keys. Source = binance or luno.")

async def setkeys(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = str(update.effective_user.id) args = context.args

if len(args) != 3:
    await update.message.reply_text("Usage: /setkeys <source> <key> <secret>")
    return

source, key, secret = args[0].lower(), args[1], args[2]
enc_key = fernet.encrypt(key.encode()).decode()
enc_secret = fernet.encrypt(secret.encode()).decode()

ref = db.reference(f'api_keys/{user_id}')
current = ref.get() or {}

if source == 'binance':
    current.update({
        'binance_api_key': enc_key,
        'binance_api_secret': enc_secret
    })
elif source == 'luno':
    current.update({
        'luno_api_key': enc_key,
        'luno_api_secret': enc_secret
    })
else:
    await update.message.reply_text("Source must be 'binance' or 'luno'")
    return

ref.set(current)
logger.info(f"Saved {source} keys for user {user_id}")
await update.message.reply_text(f"{source.capitalize()} API keys saved!")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = str(update.effective_user.id) ref = db.reference(f'api_keys/{user_id}') data = ref.get()

if not data:
    await update.message.reply_text("No API keys saved yet. Use /setkeys.")
    return

msgs = []
try:
    if 'binance_api_key' in data:
        binance = BinanceClient(
            fernet.decrypt(data['binance_api_key'].encode()).decode(),
            fernet.decrypt(data['binance_api_secret'].encode()).decode())
        bal = binance.get_asset_balance(asset='USDT')
        msgs.append(f"Binance USDT: {bal['free']}")
except Exception as e:
    msgs.append(f"Binance error: {e}")

try:
    if 'luno_api_key' in data:
        luno = LunoClient(
            fernet.decrypt(data['luno_api_key'].encode()).decode(),
            fernet.decrypt(data['luno_api_secret'].encode()).decode())
        resp = luno.get_balances()['balance']
        l_bal = "\n".join(f"{b['asset']}: {b['balance']}" for b in resp)
        msgs.append(f"Luno Balances:\n{l_bal}")
except Exception as e:
    msgs.append(f"Luno error: {e}")

await update.message.reply_text("\n\n".join(msgs))

async def arbitrage_loop(): while True: try: users = db.reference('api_keys').get() or {} for user_id, keys in users.items(): if not keys.get('binance_api_key') or not keys.get('luno_api_key'): continue

binance = BinanceClient(
                fernet.decrypt(keys['binance_api_key'].encode()).decode(),
                fernet.decrypt(keys['binance_api_secret'].encode()).decode())
            luno = LunoClient(
                fernet.decrypt(keys['luno_api_key'].encode()).decode(),
                fernet.decrypt(keys['luno_api_secret'].encode()).decode())

            bin_price = float(binance.get_symbol_ticker(symbol='BTCUSDT')['price'])
            luno_price = float(luno.get_ticker(pair='XBTZAR')['ask']) / 18.0
            diff = luno_price - bin_price

            logger.info(f"User {user_id}: Binance: {bin_price}, Luno: {luno_price}, Diff: {diff:.2f}")

    except Exception as e:
        logger.warning(f"Arbitrage loop error: {e}")
    await asyncio.sleep(30)

--- Main ---

async def main(): global telegram_app token = os.getenv("BOT_TOKEN") if not token: raise ValueError("BOT_TOKEN not set")

telegram_app = Application.builder().token(token).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("setkeys", setkeys))
telegram_app.add_handler(CommandHandler("balance", balance))

BASE_URL = os.getenv("BASE_URL", "https://crypto-bot-3-white-wind-424.fly.dev")
await telegram_app.bot.set_webhook(f"{BASE_URL}/webhook/{token}")
logger.info(f"Webhook set to {BASE_URL}/webhook/{token}")

asyncio.create_task(arbitrage_loop())

config = Config()
config.bind = ["0.0.0.0:8080"]
await serve(app, config)

if name == "main": asyncio.run(main())

