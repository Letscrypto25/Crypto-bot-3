from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref
from utils.encryption import encrypt_data, hash_password
import re

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    args = context.args

    if len(args) < 5:
        await update.message.reply_text(
            "Usage: /register <username> <password> <exchange> <api_key> <secret>"
        )
        return

    username, password, exchange, api_key, secret = args[:5]

    # Optional: enforce username rules
    if not re.match("^[a-zA-Z0-9_]{4,20}$", username):
        await update.message.reply_text("Invalid username. Use 4-20 letters, numbers, or underscores.")
        return

    # Optional: enforce password strength
    if len(password) < 6:
        await update.message.reply_text("Password must be at least 6 characters long.")
        return

    try:
        encrypted_key = encrypt_data(api_key)
        encrypted_secret = encrypt_data(secret)
        hashed_pass = hash_password(password)

        firebase_ref.child(user_id).update({
            "username": username,
            "password_hash": hashed_pass,
            "exchange": exchange.lower(),
            "api_key": encrypted_key,
            "api_secret": encrypted_secret,
            "active": True,
            "balance": 0,
            "pnl": 0,
            "portfolio": {}
        })

        await update.message.reply_text(f"Registered successfully with {exchange.capitalize()}!")
    except Exception as e:
        await update.message.reply_text(f"Registration failed: {e}")
