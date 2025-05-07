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
        'databaseURL': 'https://crypto-bot-3-default-rtdb.firebaseio.com/'  # Replace if needed
    })

# Encryption
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY not set in environment variables")
fernet = Fernet(SECRET_KEY)

# Quart app for webhook
app = Quart(__name__)
telegram_app: Application = None
initialized = False

@app.route("/")
async def health():
    return "OK", 200

@app.route("/webhook/<token>", methods=["POST"])
async def telegram_webhook(token):
    global telegram_app, initialized
    if token != os.getenv("BOT_TOKEN"):
        return "Unauthorized", 403

    if not initialized:
        await telegram_app.initialize()
        initialized = True

    update_data = await request.get_json()
    update = Update.de_json(update_data, telegram_app.bot)
    await telegram_app.process_update(update)
    return "OK", 200

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Crypto Trading Bot! Use /setkeys to set your API keys.")

async def setkeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        if len(context.args) != 4:
            raise ValueError("Usage: /setkeys <binance_key> <binance_secret> <luno_key> <luno_secret>")

        exchange_type = context.args[0].lower()

        # Only accept valid exchange types
        if exchange_type not in ['binance', 'luno']:
            raise ValueError("Invalid exchange type. Please specify 'binance' or 'luno'.")

        key, secret = context.args[1], context.args[2]

        # Encrypt the API keys
        encrypted_key = fernet.encrypt(key.encode()).decode()
        encrypted_secret = fernet.encrypt(secret.encode()).decode()

        ref = db.reference(f'api_keys/{user_id}')

        if exchange_type == "binance":
            ref.update({
                'binance_api_key': encrypted_key,
                'binance_api_secret': encrypted_secret
            })
        elif exchange_type == "luno":
            ref.update({
                'luno_api_key': encrypted_key,
                'luno_api_secret': encrypted_secret
            })

        await update.message.reply_text(f"API keys for {exchange_type} saved successfully!")
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        logger.error(f"Error in /setkeys: {e}")
        await update.message.reply_text(f"Error: {str(e)}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ref = db.reference(f'api_keys/{user_id}')
    data = ref.get()

    if data:
        msg = "\n".join([
            f"Binance API Key: {'Set' if data.get('binance_api_key') else 'Not Set'}",
            f"Binance Secret: {'Set' if data.get('binance_api_secret') else 'Not Set'}",
            f"Luno API Key: {'Set' if data.get('luno_api_key') else 'Not Set'}",
            f"Luno Secret: {'Set' if data.get('luno_api_secret') else 'Not Set'}"
        ])
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("No API keys found. Use /setkeys.")

async def deletekeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.reference(f'api_keys/{user_id}').delete()
    await update.message.reply_text("Your keys have been deleted.")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = db.reference(f'api_keys/{user_id}').get()

    if not data:
        await update.message.reply_text("No API keys found. Use /setkeys.")
        return

    try:
        # Decrypt the keys
        binance_key = fernet.decrypt(data['binance_api_key'].encode()).decode()
        binance_secret = fernet.decrypt(data['binance_api_secret'].encode()).decode()

        luno_key = fernet.decrypt(data['luno_api_key'].encode()).decode()
        luno_secret = fernet.decrypt(data['luno_api_secret'].encode()).decode()

        # Binance client setup
        binance = Client(binance_key, binance_secret)
        b_usdt = binance.get_asset_balance(asset='USDT')['free']

        # Luno client setup
        luno = LunoClient(luno_key, luno_secret)
        luno_balances = luno.get_balances()['balance']
        l_bal = "\n".join(f"{b['asset']}: {b['balance']}" for b in luno_balances)

        await update.message.reply_text(f"Binance USDT: {b_usdt}\nLuno:\n{l_bal}")
    except Exception as e:
        logger.error(f"Balance error: {e}")
        await update.message.reply_text(f"Error: {str(e)}")

# Async main function
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

    # Set webhook
    BASE_URL = os.getenv("BASE_URL", "https://crypto-bot-3-white-wind-424.fly.dev")
    await telegram_app.bot.set_webhook(f"{BASE_URL}/webhook/{token}")
    logger.info(f"Webhook set to {BASE_URL}/webhook/{token}")

    # Run Quart server
    config = Config()
    config.bind = ["0.0.0.0:8080"]
    await serve(app, config)

if __name__ == "__main__":
    asyncio.run(main())
