# handlers/register.py

from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    args = context.args

    if len(args) < 3:
        await update.message.reply_text("Usage: /register <exchange> <api_key> <secret>")
        return

    exchange, api_key, secret = args[:3]

    try:
        firebase_ref.child(user_id).update({
            "username": user.username or f"user_{user_id[-4:]}",
            "exchange": exchange.lower(),
            "api_key": api_key,
            "api_secret": secret,
            "active": True,
            "balance": 0,
            "pnl": 0,
            "portfolio": {}
        })

        await update.message.reply_text(f"Registered with {exchange.capitalize()}! You are now active.")
    except Exception as e:
        await update.message.reply_text(f"Registration failed: {e}")
