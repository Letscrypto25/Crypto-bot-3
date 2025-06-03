from telegram import Update
from telegram.ext import ContextTypes
from firebase_admin import db

async def setamount_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args

    if not args:
        await update.message.reply_text("Usage: /setamount <amount>")
        return

    try:
        amount = float(args[0])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please enter a valid positive number for amount.")
        return

    # Save amount to Firebase
    db.reference(f"/users/{user_id}/settings").update({"amount": amount})

    await update.message.reply_text(f"✅ Trade amount saved to cloud: {amount}")
