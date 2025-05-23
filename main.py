import os
import json
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import threading
import asyncio
from datetime import datetime

# Firebase setup
with open('firebase_encoded.txt', 'r') as f:
    firebase_data = json.load(f)
cred = credentials.Certificate(firebase_data)
firebase_admin.initialize_app(cred, {
    'databaseURL': firebase_data['databaseURL']
})

# Telegram setup
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
ALLOWED_USERS = [7521070576]  # Replace with your Telegram user ID(s)

# Flask app for webhook
app = Flask(__name__)

# Helper to get user reference
def user_ref(user_id):
    return db.reference(f"users/{user_id}")

def leaderboard_ref():
    return db.reference("leaderboard")

# Command handlers
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
    msg = "Last 10 trades:\n"
    for trade in history[-10:]:
        msg += f"{trade}\n"
    await update.message.reply_text(msg)

# Auto trading logic (simplified)
def auto_trading_logic():
    users = db.reference("users").get() or {}
    for user_id, data in users.items():
        portfolio = data.get("portfolio", {})
        balance = data.get("balance", 0)

        if "BTC" not in portfolio and balance >= 500:
            buy_amount = 100  # example fixed amount
            new_balance = balance - buy_amount
            portfolio["BTC"] = portfolio.get("BTC", 0) + buy_amount / 50000  # mock BTC price

            # Save updates
            user_ref(user_id).update({"balance": new_balance, "portfolio": portfolio})
            hist_ref = user_ref(user_id).child("history")
            history = hist_ref.get() or []
            history.append(f"Bought BTC worth $100 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            hist_ref.set(history)

            # Update leaderboard
            total_value = new_balance + portfolio["BTC"] * 50000
            leaderboard_ref().child(user_id).set(total_value)

# Periodic trading scheduler
def schedule_trading():
    auto_trading_logic()
    threading.Timer(60, schedule_trading).start()

schedule_trading()

# Create telegram application and add handlers
app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()

app_telegram.add_handler(CommandHandler("start", start))
app_telegram.add_handler(CommandHandler("balance", balance))
app_telegram.add_handler(CommandHandler("portfolio", portfolio))
app_telegram.add_handler(CommandHandler("leaderboard", leaderboard))
app_telegram.add_handler(CommandHandler("trade_history", trade_history))

# Flask webhook route
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.run(app_telegram.process_update(update))
    return "ok"

@app.route("/")
def index():
    return "Bot is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
