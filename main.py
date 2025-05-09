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

# Tournament logic - for simplicity
user_approvals = {}
autobot_tasks = {}

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

def update_leaderboard():
    leaderboard_ref = db.reference("leaderboard")
    leaderboard = leaderboard_ref.get() or {}

    # Update leaderboard with player stats
    for user_id in leaderboard:
        user_data = db.reference(f"tournaments/{user_id}").get()
        if user_data:
            leaderboard[user_id] = user_data.get("profit_percent", 0)
    
    sorted_leaderboard = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)
    db.reference("leaderboard").set(sorted_leaderboard)

# Tournament logic
async def stopbot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)

    # Check if bot is running
    if telegram_id not in autobot_tasks:
        await update.message.reply_text("No active autobot found.")
        return

    # Check payment or approval
    user_data = db.child("users").child(telegram_id).get().val()
    has_paid = user_data.get("has_paid", False)

    if has_paid:
        autobot_tasks[telegram_id].cancel()
        del autobot_tasks[telegram_id]
        await update.message.reply_text("Autobot stopped. Thank you for supporting the app!")
        return

    if user_approvals.get(telegram_id) == "approved":
        # Deduct fees, send profile, and register tournament
        await finalize_stop(update, telegram_id, user_data)
        return

    # Ask for approval
    await update.message.reply_text(
        "To stop the autobot, approve tournament fee (1.25%) and profit share (0.25–0.5%).\n\n"
        "Type `approve` to continue."
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    text = update.message.text.lower()

    if text == "approve" and telegram_id in autobot_tasks:
        user_approvals[telegram_id] = "approved"
        user_data = db.child("users").child(telegram_id).get().val()
        await finalize_stop(update, telegram_id, user_data)

async def finalize_stop(update, telegram_id, user_data):
    # Cancel autobot
    autobot_tasks[telegram_id].cancel()
    del autobot_tasks[telegram_id]

    # Simulate sending profile and deductions
    username = user_data.get("username", "unknown")
    profits = user_data.get("profits", 0)
    tournament_fee = profits * 0.0125
    app_cut = profits * 0.0025

    # Update leaderboard
    update_leaderboard()

    await update.message.reply_text(
        f"Autobot stopped.\n\nProfile: @{username}\nProfits: ${profits:.2f}\n"
        f"Deducted: ${tournament_fee:.2f} for tournament + ${app_cut:.2f} for app.\n"
        f"You’re now registered in the tournament. Good luck!"
    )

    # Save status
    db.child("users").child(telegram_id).update({
        "registered_tournament": True,
        "has_paid": True
    })

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leaderboard_ref = db.reference("leaderboard")
    leaderboard = leaderboard_ref.get() or []

    if not leaderboard:
        await update.message.reply_text("No leaderboard available.")
        return

    leaderboard_message = "Leaderboard:\n"
    for rank, (user_id, profit_percent) in enumerate(leaderboard[:10], start=1):
        user_data = db.child("users").child(user_id).get().val()
        username = user_data.get("username", "unknown")
        leaderboard_message += f"{rank}. @{username}: {profit_percent:.2f}%\n"

    await update.message.reply_text(leaderboard_message)

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
        "/leaderboard - View the tournament leaderboard\n"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

# Setkeys command handler to save API keys
async def setkeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)

    # Extract exchange, API key, and secret from the command arguments
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /setkeys <exchange> <api_key> <api_secret>")
        return

    exchange = context.args[0].lower()
    api_key = context.args[1]
    api_secret = context.args[2]

    if exchange not in ["binance", "luno"]:
        await update.message.reply_text("Supported exchanges: Binance, Luno.")
        return

    # Save API keys to Firebase under the user’s Telegram ID
    db.reference(f"api_keys/{telegram_id}/{exchange}").set({
        "api_key": api_key,
        "api_secret": api_secret
    })

    await update.message.reply_text(f"API keys for {exchange.capitalize()} saved successfully.")

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
    telegram_app.add_handler(CommandHandler("leaderboard", leaderboard))

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
