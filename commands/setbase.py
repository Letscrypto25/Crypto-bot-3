from telegram import Update
from telegram.ext import ContextTypes
from firebase_admin import db

async def setbase_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args

    if not args:
        await update.message.reply_text("Usage: /setbase <currency_code> (e.g. USD, BTC, ETH)")
        return

    base_currency = args[0].upper()

    # Save base currency to Firebase
    db.reference(f"/users/{user_id}/settings").update({"base_currency": base_currency})

    await update.message.reply_text(f"✅ Base currency saved to cloud: {base_currency}")
