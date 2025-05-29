from telegram import Update
from telegram.ext import ContextTypes
from firebase_admin import db

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    try:
        user_data = db.reference(f"users/{user_id}").get()
        if not user_data or "exchange" not in user_data:
            await update.message.reply_text("Exchange not set. Please configure your API keys.")
            return

        exchange = user_data["exchange"]
        balances = get_balance(user_id=user_id, source=exchange)

        if not balances:
            await update.message.reply_text("You have no assets with a positive balance.")
            return

        message = f"📊 *Your {exchange.capitalize()} Balances:*\n"
        for asset, amount in balances.items():
            message += f"• `{asset}`: *{amount:.6f}*\n"

        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        print(f"[Handler Error] /balance: {e}")
        try:
            # fallback to old balance field in Firebase
            user_ref = db.reference(f"users/{user_id}/balance")
            fallback_balance = user_ref.get() or 0.0
            await update.message.reply_text(f"Your current balance is: {fallback_balance} USD")
        except:
            await update.message.reply_text("Sorry, could not fetch your balance right now.")
