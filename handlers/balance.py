from telegram import Update
from telegram.ext import ContextTypes
from firebase_admin import db

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    try:
        user_ref = db.reference(f"users/{user_id}/balance")
        balance = user_ref.get()
        if balance is None:
            balance = 0.0
    except Exception as e:
        await update.message.reply_text("Sorry, could not fetch your balance right now.")
        return

    await update.message.reply_text(f"Your current balance is: {balance} USD")
