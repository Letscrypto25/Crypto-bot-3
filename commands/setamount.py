from telegram import Update
from telegram.ext import ContextTypes

user_amounts = {}

async def setamount_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
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

    user_amounts[user_id] = amount
    await update.message.reply_text(f"Trade amount set to: {amount}")
