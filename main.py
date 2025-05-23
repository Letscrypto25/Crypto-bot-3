import os
import json
import requests
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
import threading
from datetime import datetime
import asyncio

# Load Firebase credentials
with open("firebase_encoded.txt", "r") as f:
    firebase_data = json.load(f)

cred = credentials.Certificate(firebase_data)
firebase_admin.initialize_app(cred, {
    "databaseURL": firebase_data["databaseURL"]
})

# Telegram bot
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise Exception("TELEGRAM_BOT_TOKEN not set")
ALLOWED_USERS = [7521070576]

# Firebase helpers
def user_ref(uid): return db.reference(f"users/{uid}")
def leaderboard_ref(): return db.reference("leaderboard")

# Create app
flask_app = Flask(__name__)
bot_app = Application.builder().token(BOT_TOKEN).build()

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ALLOWED_USERS:
        await update.message.reply_text("Access Denied.")
        return
    ref = user_ref(uid)
    if not ref.get():
        ref.set({"balance": 1000.0, "portfolio": {}, "history": []})
        await update.message.reply_text("Welcome! Account created with $1000.")
    else:
        await update.message.reply_text("Welcome back!")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    data = user_ref(uid).get()
    if data:
        await update.message.reply_text(f"Your balance: ${data.get('balance', 0):.2f}")

async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    holdings = user_ref(uid).child("portfolio").get() or {}
    if not holdings:
        await update.message.reply_text("Portfolio is empty.")
        return
    text = "\n".join([f"{k}: {v}" for k, v in holdings.items()])
    await update.message.reply_text("Your portfolio:\n" + text)

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lb = leaderboard_ref().get() or {}
    sorted_lb = sorted(lb.items(), key=lambda x: x[1], reverse=True)
    msg = "Leaderboard:\n"
    for i, (uid, score) in enumerate(sorted_lb[:10], 1):
        msg += f"{i}. User {uid}: ${score:.2f}\n"
    await update.message.reply_text(msg)

async def trade_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    hist = user_ref(uid).child("history").get() or []
    if not hist:
        await update.message.reply_text("No trades yet.")
        return
    await update.message.reply_text("Last 10 trades:\n" + "\n".join(hist[-10:]))

# Register handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("balance", balance))
bot_app.add_handler(CommandHandler("portfolio", portfolio))
bot_app.add_handler(CommandHandler("leaderboard", leaderboard))
bot_app.add_handler(CommandHandler("trade_history", trade_history))

# Trading logic
def auto_trading_logic():
    users = db.reference("users").get() or {}
    for uid, data in users.items():
        portfolio = data.get("portfolio", {})
        balance = data.get("balance", 0)

        if "BTC" not in portfolio and balance >= 500:
            buy_amt = 100
            new_bal = balance - buy_amt
            portfolio["BTC"] = portfolio.get("BTC", 0) + buy_amt / 50000

            user_ref(uid).update({"balance": new_bal, "portfolio": portfolio})
            hist = user_ref(uid).child("history").get() or []
            hist.append(f"Bought BTC for $100 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            user_ref(uid).child("history").set(hist)

            total_val = new_bal + portfolio["BTC"] * 50000
            leaderboard_ref().child(uid).set(total_val)

def schedule_trading():
    auto_trading_logic()
    threading.Timer(60, schedule_trading).start()

# Start trading loop
schedule_trading()

# Webhook route
@flask_app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    await bot_app.process_update(update)
    return "ok"

@flask_app.route("/")
def index():
    return "Bot running!"

# Start Flask
def main():
    bot_app.run_polling()  # this can be replaced by webhook setup if preferred

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)
