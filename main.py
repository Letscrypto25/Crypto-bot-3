import os
import logging
import asyncio
import json
import tempfile
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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Firebase credentials from env and write to a temp file
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

# Encryption setup
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY not set in environment variables")
fernet = Fernet(SECRET_KEY)

# Quart app
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
    logger.info(f"Webhook received: {json.dumps(update_data)}")

    update = Update.de_json(update_data, telegram_app.bot)
    print(">> FULL TEXT MESSAGE:", update.message.text if update.message else "No message")
    await telegram_app.process_update(update)
    return "OK", 200

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Crypto Trading Bot! Use /setkeys to set your API keys.\n\nExample:\n/setkeys binance BINANCE_API_KEY BINANCE_SECRET")

# Command: /setkeys <exchange> <api_key> <api_secret>
async def setkeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        if len(context.args) != 3:
            raise ValueError("Usage: /setkeys <exchange> <api_key> <api_secret>")

        exchange = context.args[0].lower()
        if exchange not in ["binance", "luno"]:
            raise ValueError("Exchange must be 'binance' or 'luno'")

        api_key, api_secret = context.args[1], context.args[2]
        encrypted_key = fernet.encrypt(api_key.encode()).decode()
        encrypted_secret = fernet.encrypt(api_secret.encode()).decode()

        ref = db.reference(f'api_keys/{user_id}')
        if exchange == "binance":
            ref.update({
                'binance_api_key': encrypted_key,
                'binance_api_secret': encrypted_secret
            })
        else:
            ref.update({
                'luno_api_key': encrypted_key,
                'luno_api_secret': encrypted_secret
            })

        await update.message.reply_text(f"{exchange.capitalize()} keys saved successfully.")
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        logger.error(f"SetKeys error: {e}")
        await update.message.reply_text("Something went wrong while saving your keys.")

# Command: /status
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ref = db.reference(f'api_keys/{user_id}')
    data = ref.get()

    if not data:
        await update.message.reply_text("No API keys saved yet. Use /setkeys.")
        return

    response = [
        f"Binance API Key: {'Set' if data.get('binance_api_key') else 'Not Set'}",
        f"Binance Secret: {'Set' if data.get('binance_api_secret') else 'Not Set'}",
        f"Luno API Key: {'Set' if data.get('luno_api_key') else 'Not Set'}",
        f"Luno Secret: {'Set' if data.get('luno_api_secret') else 'Not Set'}"
    ]
    await update.message.reply_text("\n".join(response))

# Command: /deletekeys
async def deletekeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.reference(f'api_keys/{user_id}').delete()
    await update.message.reply_text("Your saved keys have been deleted.")

# Command: /balance
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = db.reference(f'api_keys/{user_id}').get()

    if not data:
        await update.message.reply_text("No keys found. Use /setkeys.")
        return

    try:
        binance_key = fernet.decrypt(data['binance_api_key'].encode()).decode()
        binance_secret = fernet.decrypt(data['binance_api_secret'].encode()).decode()
        binance = Client(binance_key, binance_secret)
        b_balance = binance.get_asset_balance(asset='USDT')
        b_usdt = b_balance['free'] if b_balance else '0.0'

        luno_key = fernet.decrypt(data['luno_api_key'].encode()).decode()
        luno_secret = fernet.decrypt(data['luno_api_secret'].encode()).decode()
        luno = LunoClient()
        luno.set_auth(luno_key, luno_secret)
        l_bal = luno.get_balances()['balance']
        luno_summary = "\n".join([f"{b['asset']}: {b['balance']}" for b in l_bal])

        await update.message.reply_text(f"Binance USDT: {b_usdt}\n\nLuno:\n{luno_summary}")
    except Exception as e:
        logger.error(f"Balance fetch error: {e}")
        await update.message.reply_text(f"Error fetching balances: {e}")

# Start bot + Quart server
async def main():
    global telegram_app
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN not set")

    telegram_app = Application.builder().token(token).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("setkeys", setkeys))
    telegram_app.add_handler(CommandHandler("status", status))
    telegram_app.add_handler(CommandHandler("deletekeys", deletekeys))
    telegram_app.add_handler(CommandHandler("balance", balance))

    await telegram_app.initialize()
    await telegram_app.start()

    BASE_URL = os.getenv("BASE_URL", "https://crypto-bot-3-white-wind-424.fly.dev")
    await telegram_app.bot.set_webhook(f"{BASE_URL}/webhook/{token}")
    logger.info(f"Webhook set to {BASE_URL}/webhook/{token}")

    config = Config()
    config.bind = ["0.0.0.0:8080"]
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(main())
