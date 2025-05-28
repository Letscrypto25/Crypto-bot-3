from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref
from encryption import verify_password

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    args = context.args

    if len(args) < 2:
        await update.message.reply_text("Usage: /login <username> <password>")
        return

    username_input, password_input = args[:2]

    try:
        all_users = firebase_ref.get()

        # Match username and check password
        for uid, data in all_users.items():
            if data.get("username") == username_input:
                if verify_password(password_input, data.get("password_hash")):
                    firebase_ref.child(user_id).update({
                        "logged_in": True,
                        "session_user": username_input
                    })
                    await update.message.reply_text("Login successful.")
                    return
                else:
                    await update.message.reply_text("Incorrect password.")
                    return

        await update.message.reply_text("Username not found.")

    except Exception as e:
        await update.message.reply_text(f"Login failed: {e}")
