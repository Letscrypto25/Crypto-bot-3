import os
import logging
import time
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler

# --- Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)

# --- Environment ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is required")

bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)

# --- Firebase ---
cred = credentials.Certificate("firebase_admin_credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# --- Commands ---

def start(update, context):
    user = update.message.from_user
    telegram_id = str(user.id)
    username = user.username or "unknown"

    user_ref = db.collection("users").document(telegram_id)
    user_doc = user_ref.get()

    if user_doc.exists:
        update.message.reply_text("Welcome back!")
    else:
        user_ref.set({
            "telegram_id": telegram_id,
            "username": username,
            "balance": 100,
            "joined_at": firestore.SERVER_TIMESTAMP,
            "last_action": "start",
            "subscribed": True,
            "preferred_strategy": "arbitrage"
        })
        update.message.reply_text("Your account has been created.")

def set_strategy(update, context):
    if len(context.args) != 1:
        update.message.reply_text("Usage: /set_strategy <strategy_name>")
        return

    strategy = context.args[0]
    telegram_id = str(update.message.from_user.id)

    user_ref = db.collection("users").document(telegram_id)
    if user_ref.get().exists:
        user_ref.update({
            "preferred_strategy": strategy,
            "last_action": "set_strategy"
        })
        update.message.reply_text(f"Strategy set to '{strategy}'.")
    else:
        update.message.reply_text("Please use /start first.")

def trade(update, context):
    telegram_id = str(update.message.from_user.id)
    user_ref = db.collection("users").document(telegram_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        update.message.reply_text("Please use /start first.")
        return

    strategy = user_doc.get("preferred_strategy")
    profit = round(1 + (time.time() % 5), 2)  # simulate 1% to 5% profit

    trade_data = {
        "timestamp": firestore.SERVER_TIMESTAMP,
        "strategy": strategy,
        "profit": profit,
        "status": "completed"
    }

    db.collection("trades").add(trade_data)
    user_ref.update({"last_action": "trade"})
    update.message.reply_text(f"Trade executed with strategy '{strategy}'. Profit: {profit}%")

# --- Register handlers ---
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("set_strategy", set_strategy))
dispatcher.add_handler(CommandHandler("trade", trade))

# --- Webhook ---
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "Bot is running."

@app.before_first_request
def set_webhook():
    if WEBHOOK_URL:
        full_url = f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
        bot.set_webhook(full_url)
        logger.info(f"Webhook set: {full_url}")
    else:
        logger.warning("WEBHOOK_URL not set.")

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 8080)), host="0.0.0.0")
