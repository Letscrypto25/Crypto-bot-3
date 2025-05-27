# handlers/register.py

from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref
from utils.encryption import encrypt_data, hash_password
from datetime import datetime
from firebase_admin import db
from utils.logging import log_event  # Optional: move to shared log_event if used in main.py

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    args = context.args

    if len(args) < 5:
        await update.message.reply_text(
            "Usage: /register <exchange> <api_key> <secret> <username> <password>"
        )
        return

    exchange, api_key, api_secret, username, password = args[:5]

    # Check if username already exists
    existing = db.reference("users").get()
    for uid, data in (existing or {}).items():
        if data.get("username", "").lower() == username.lower():
            await update.message.reply_text("This username is already taken. Choose another.")
            return

    try:
        encrypted_key = encrypt_data(api_key)
        encrypted_secret = encrypt_data(api_secret)
        hashed_pw = hash_password(password)

        firebase_ref.child(user_id).update({
            "exchange": exchange.lower(),
            "api_key": encrypted_key,
            "api_secret": encrypted_secret,
            "username": username,
            "password": hashed_pw,
            "active": True,
            "balance": 0,
            "pnl": 0,
            "portfolio": {},
            "registered_at": datetime.utcnow().isoformat()
        })

        await update.message.reply_text(f"Registered with {exchange.capitalize()} successfully!")
        log_event(user_id, "register", f"Registered with exchange: {exchange}")
    except Exception as e:
        await update.message.reply_text(f"Registration failed: {e}")
        log_event(user_id, "register", "Registration error", status="error", error=e)
