import os
import json
import asyncio
import requests
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)
from datetime import datetime
import threading

# Firebase setup
with open('firebase_encoded.txt', 'r') as f:
    firebase_data = json.load(f)
cred = credentials.Certificate(firebase_data)
firebase_admin.initialize_app(cred, {
    'databaseURL': firebase_data['databaseURL']
})

# Telegram setup
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set in environment.")
bot = Bot(token=BOT_TOKEN)
ALLOWED_USERS = [7521070576]  # Replace with your Telegram user ID(s)

# Flask app
app = Flask(__name__)

# Firebase paths
def user_ref(user_id):
    return db.reference(f"users/{user_id}")

def leaderboard_ref():
    return db.reference("leaderboard")

# Telegram command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("Access Denied.")
        return
    ref = user_ref(user_id)
    if not ref.get():
        ref.set({"balance": 1000.0, "portfolio": {}, "history": []})
        await update.message.reply_text("Welcome! Account created with $1000.")
    else:
        await update.message.reply_text("Welcome back!")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_ref(user_id).get()
    if data:
        await update.message.reply_text(f"Your balance: ${data.get('balance', 0):.2f}")

async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    holdings = user_ref(user_id).child("portfolio").get() or {}
    if not holdings:
        await update.message.reply_text("Your portfolio is empty.")
        return
    msg = "Your portfolio:\n" + "\n".join([f"{k}: {v}" for k, v in holdings.items()])
    await update.message.reply_text(msg)

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lb = leaderboard_ref().get() or {}
    sorted_lb = sorted(lb.items(), key=lambda x: x[1], reverse=True)
    msg = "Leaderboard:\n"
    for i, (user_id, score) in enumerate(sorted_lb[:10], 1):
        msg += f"{i}. User {user_id}: ${score:.2f}\n"
    await update.message.reply_text(msg)

async def trade_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    history = user_ref(user_id).child("history").get() or []
    if not history:
        await update.message.reply_text("No trade history yet.")
        return
    msg = "Last 10 trades:\n" + "\n".join(history[-10:])
    await update.message.reply_text(msg)

# Auto trading logic
def auto_trading_logic():
    users = db.reference("users").get() or {}
    for user_id, data in users.items():
        portfolio = data.get("portfolio", {})
        balance = data.get("balance", 0)
        if "BTC" not in portfolio and balance >= 500:
            buy_amount = 100
            new_balance = balance - buy_amount
            portfolio["BTC"] = portfolio.get("BTC", 0) + buy_amount / 50000
            user_ref(user_id).update({"balance": new_balance, "portfolio": portfolio})
            hist_ref = user_ref(user_id).child("history")
            history = hist_ref.get() or []
            history.append(f"Bought BTC worth $100 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            hist_ref.set(history)
            total_value = new_balance + portfolio["BTC"] * 50000
            leaderboard_ref().child(user_id).set(total_value)

def schedule_trading():
    auto_trading_logic()
    threading.Timer(60, schedule_trading).start()

# Start periodic trading
schedule_trading()

# Create Telegram application
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("balance", balance))
telegram_app.add_handler(CommandHandler("portfolio", portfolio))
telegram_app.add_handler(CommandHandler("leaderboard", leaderboard))
telegram_app.add_handler(CommandHandler("trade_history", trade_history))

# Webhook route
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.create_task(telegram_app.process_update(update))
    return "ok"

# Root route
@app.route("/")
def index():
    return "Bot is running."

# Run everything
if __name__ == "__main__":
    telegram_app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=f"https://yourdomain.com/{BOT_TOKEN}",  # replace with actual domain
        allowed_updates=Update.ALL_TYPES
    )
