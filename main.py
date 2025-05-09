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

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Firebase initialization
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

# Fernet key
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY not set")
fernet = Fernet(SECRET_KEY)

# Quart app setup
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

# Helpers
def save_trade(telegram_id, trade_data):
    ref = db.reference(f"trades/{telegram_id}")
    ref.push(trade_data)

def send_alert(telegram_id, alert_msg):
    ref = db.reference(f"alerts/{telegram_id}")
    ref.push({
        "message": alert_msg,
        "timestamp": datetime.now().isoformat()
    })

def update_tournament_score(telegram_id, profit_percent, trades_count):
    ref = db.reference(f"tournaments/{telegram_id}")
    ref.set({
        "profit_percent": profit_percent,
        "trades": trades_count,
        "last_updated": datetime.now().isoformat()
    })

def save_error_to_firebase(error_message):
    ref = db.reference("errors")
    error_ref = ref.push({
        "error": error_message,
        "timestamp": datetime.now().isoformat()
    })
    return error_ref.key

# Telegram commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Crypto Bot! Use /help for commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "**Available Commands:**\n\n"
        "/start - Welcome message\n"
        "/help - This help info\n"
        "/setkeys <exchange> <api_key> <api_secret> - Save your API keys\n"
        "/status - Check if your keys are saved\n"
        "/deletekeys - Delete all saved keys\n"
        "/balance - Check your Binance & Luno balances\n"
        "/trades - Show your saved trades\n"
        "/tournament - Show your tournament stats\n"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def setkeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        if len(context.args) != 3:
            raise ValueError("Usage: /setkeys <exchange> <api_key> <api_secret>")

        exchange = context.args[0].lower()
        if exchange not in ['binance', 'luno']:
            raise ValueError("Invalid exchange. Use 'binance' or 'luno'.")

        api_key = fernet.encrypt(context.args[1].encode()).decode()
        api_secret = fernet.encrypt(context.args[2].encode()).decode()
        ref = db.reference(f'api_keys/{user_id}')

        if exchange == "binance":
            ref.update({'binance_api_key': api_key, 'binance_api_secret': api_secret})
        else:
            ref.update({'luno_api_key': api_key, 'luno_api_secret': api_secret})

        await update.message.reply_text(f"{exchange.title()} keys saved.")
    except Exception as e:
        logger.error(f"Setkeys error: {e}")
        error_url = save_error_to_firebase(str(e))
        await update.message.reply_text(f"Error: {str(e)}. More details: {error_url}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = db.reference(f'api_keys/{user_id}').get()
    if data:
        msg = "\n".join([
            f"Binance Key: {'Set' if data.get('binance_api_key') else 'Not Set'}",
            f"Luno Key: {'Set' if data.get('luno_api_key') else 'Not Set'}"
        ])
    else:
        msg = "No API keys saved."
    await update.message.reply_text(msg)

async def deletekeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.reference(f'api_keys/{user_id}').delete()
    await update.message.reply_text("Keys deleted.")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = db.reference(f'api_keys/{user_id}').get()
    if not data:
        await update.message.reply_text("Set your keys first using /setkeys")
        return
    try:
        msg = ""

        if 'binance_api_key' in data:
            b_key = fernet.decrypt(data['binance_api_key'].encode()).decode()
            b_secret = fernet.decrypt(data['binance_api_secret'].encode()).decode()
            b_client = Client(b_key, b_secret)
            usdt = b_client.get_asset_balance(asset='USDT')['free']
            msg += f"Binance USDT: {usdt}\n"

        if 'luno_api_key' in data:
            l_key = fernet.decrypt(data['luno_api_key'].encode()).decode()
            l_secret = fernet.decrypt(data['luno_api_secret'].encode()).decode()
            l_client = LunoClient()
            l_client.set_auth(l_key, l_secret)
            balances = l_client.get_balances()['balance']
            msg += "Luno:\n" + "\n".join(f"{b['asset']}: {b['balance']}" for b in balances)

        await update.message.reply_text(msg or "No balances found.")
    except Exception as e:
        logger.error(f"Balance error: {e}")
        error_url = save_error_to_firebase(str(e))
        await update.message.reply_text(f"Error checking balance. More details: {error_url}")

async def trades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ref = db.reference(f"trades/{user_id}")
    data = ref.get()
    if not data:
        await update.message.reply_text("No trades saved yet.")
        return

    lines = []
    for k, v in list(data.items())[-5:]:
        lines.append(f"{v.get('symbol', '?')} - {v.get('side', '?')} @ {v.get('price', '?')}")
    await update.message.reply_text("Your Recent Trades:\n" + "\n".join(lines))

async def tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ref = db.reference(f"tournaments/{user_id}")
    data = ref.get()
    if not data:
        await update.message.reply_text("No tournament stats yet.")
        return

    msg = (
        f"Profit %: {data.get('profit_percent', '0')}\n"
        f"Trades: {data.get('trades', '0')}\n"
        f"Last Updated: {data.get('last_updated', '?')}"
    )
    await update.message.reply_text("Tournament Stats:\n" + msg)

# Main function
async def main():
    global telegram_app
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN not set")

    telegram_app = Application.builder().token(token).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("setkeys", setkeys))
    telegram_app.add_handler(CommandHandler("status", status))
    telegram_app.add_handler(CommandHandler("deletekeys", deletekeys))
    telegram_app.add_handler(CommandHandler("balance", balance))
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
