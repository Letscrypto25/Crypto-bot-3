from telegram import Update
from telegram.ext import ContextTypes
from firebase_admin import db
import datetime

# Utility functions

def get_leaderboard():
    users_ref = db.reference('users')
    users_data = users_ref.get() or {}
    leaderboard = []
    for user_id, user_info in users_data.items():
        username = user_info.get('username', 'Unknown')
        balance = float(user_info.get('balance', 0))
        leaderboard.append((username, balance))
    leaderboard.sort(key=lambda x: x[1], reverse=True)
    return leaderboard

# Telegram command handlers

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    username = user.username or user.first_name
    users_ref = db.reference('users')
    user_ref = users_ref.child(user_id)
    if not user_ref.get():
        user_ref.set({
            'username': username,
            'balance': 1000.0,
            'portfolio': {},
            'trades': []
        })
    await update.message.reply_text(f"Welcome {username}! Your account has been initialized with $1000.")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_ref = db.reference(f'users/{user_id}')
    user_data = user_ref.get()
    if user_data:
        balance = user_data.get('balance', 0.0)
        await update.message.reply_text(f"Your current balance is ${balance:.2f}")
    else:
        await update.message.reply_text("You need to /start first to initialize your account.")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leaderboard_data = get_leaderboard()
    message = "\n".join([f"{i+1}. {name}: ${balance:.2f}" for i, (name, balance) in enumerate(leaderboard_data)])
    await update.message.reply_text("Leaderboard:\n" + message)

async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_ref = db.reference(f'users/{user_id}')
    user_data = user_ref.get()
    if user_data:
        portfolio = user_data.get('portfolio', {})
        if portfolio:
            lines = [f"{symbol}: {data['amount']} units @ Avg Price ${data['avg_price']:.2f}" for symbol, data in portfolio.items()]
            await update.message.reply_text("Your Portfolio:\n" + "\n".join(lines))
        else:
            await update.message.reply_text("Your portfolio is empty.")
    else:
        await update.message.reply_text("You need to /start first to initialize your account.")

async def trade_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_ref = db.reference(f'users/{user_id}/trades')
    trades = user_ref.get()
    if trades:
        lines = [f"[{trade['timestamp']}] {trade['type'].upper()} {trade['symbol']} @ ${trade['price']} x {trade['amount']}" for trade in trades[-10:]]
        await update.message.reply_text("Last 10 Trades:\n" + "\n".join(lines))
    else:
        await update.message.reply_text("No trades found.")
