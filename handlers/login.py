# handlers/login.py

from telegram import Update
from telegram.ext import ContextTypes
from firebase_admin import db
from utils.encryption import verify_password
from utils.logging import log_event  # reuse your log_event

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user = update.effective_user
    user_id = str(user.id)

    if len(args) < 2:
        await update.message.reply_text("Usage: /login <username> <password>")
        return

    username_input, password_input = args[:2]

    try:
        all_users = db.reference("users").get()
        matched_user = None
        matched_uid = None

        for uid, user_data in (all_users or {}).items():
            if user_data.get("username", "").lower() == username_input.lower():
                if verify_password(password_input, user_data.get("password", "")):
                    matched_user = user_data
                    matched_uid = uid
                    break

        if matched_user:
            # Optionally update Telegram ID in case a new one logs in
            db.reference(f"users/{matched_uid}/telegram_id").set(user_id)
            await update.message.reply_text("Login successful. You're now authenticated.")
            log_event(user_id, "login", f"Logged in as {username_input}")
        else:
            await update.message.reply_text("Login failed: Invalid username or password.")
            log_event(user_id, "login", "Invalid login attempt", status="error")
    except Exception as e:
        await update.message.reply_text(f"Login failed: {e}")
        log_event(user_id, "login", "Login error", status="error", error=e)
