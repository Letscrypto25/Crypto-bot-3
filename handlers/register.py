# handlers/register.py

from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args

    if len(args) < 3:
        await update.message.reply_text("Usage: /register <exchange> <api_key> <secret>")
        return

    exchange, api_key, secret = args[0], args[1], args[2]

    firebase_ref.child(user_id).update({
        "exchange": exchange,
        "api_key": api_key,
        "api_secret": secret,
        "active": True
    })

    await update.message.reply_text(f"Registered with {exchange.capitalize()}! You are now active.")
