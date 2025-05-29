from telegram import Update
from telegram.ext import ContextTypes
from firebase_admin import db
from your_module import get_balance  # Make sure this import is correct

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    print(f"[Balance Handler] User: {user_id}")

    try:
        user_data = db.reference(f"users/{user_id}").get()
        print(f"[Balance Handler] User data: {user_data}")

        if not user_data or "exchange" not in user_data:
            await update.message.reply_text("⚠️ Exchange not set. Please configure your API keys.")
            return

        exchange = user_data["exchange"]
        balances = get_balance(user_id=user_id, source=exchange)
        print(f"[Balance Handler] {exchange} balances: {balances}")

        if not balances:
            await update.message.reply_text("ℹ️ You have no assets with a positive balance.")
            return

        message = f"📊 *Your {exchange.capitalize()} Balances:*\n"
        for asset, amount in balances.items():
            message += f"• `{asset}`: *{amount:.6f}*\n"

        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        print(f"[Handler Error] /balance: {e}")
        try:
            # fallback to legacy balance field in Firebase
            fallback = db.reference(f"users/{user_id}/balance").get()
            fallback_balance = fallback if fallback is not None else 0.0
            await update.message.reply_text(f"💰 Legacy Balance: {fallback_balance} USD")
        except Exception as fallback_error:
            print(f"[Fallback Error] /balance: {fallback_error}")
            await update.message.reply_text("❌ Could not fetch your balance right now.")
