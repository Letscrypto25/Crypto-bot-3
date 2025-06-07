from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from firebase_admin import db
from encryption import decrypt_data
from exchanges import get_balance

def safe_decrypt(encrypted_value):
    if not encrypted_value:
        return None
    try:
        if isinstance(encrypted_value, bytes):
            encrypted_value = encrypted_value.decode("utf-8")
        return decrypt_data(encrypted_value)
    except Exception as e:
        print(f"[Decryption Error] {e}")
        return None

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

        if exchange == "luno":
            api_key_encrypted = user_data.get("luno_api_key")
            secret_encrypted = user_data.get("luno_api_secret")
        elif exchange == "binance":
            api_key_encrypted = user_data.get("binance_api_key")
            secret_encrypted = user_data.get("binance_api_secret")
        else:
            await update.message.reply_text("❌ Unsupported exchange configured.")
            return

        api_key = safe_decrypt(api_key_encrypted)
        secret = safe_decrypt(secret_encrypted)

        if not api_key or not secret:
            await update.message.reply_text("⚠️ API credentials missing or invalid. Please /register again.")
            return

        # Prepare user dict for get_balance
        user = {
            f"{exchange}_api_key": api_key,
            f"{exchange}_api_secret": secret,
        }

        balances = get_balance(user_id=user_id, source=exchange, user=user)
        print(f"[Balance Handler] {exchange} balances: {balances}")

        if not balances:
            await update.message.reply_text("ℹ️ You have no assets with a positive balance.")
            return

        message = f"📊 *Your {exchange.capitalize()} Balances:*\n"
        for asset, amount in balances.items():
            message += f"• `{asset.upper()}`: *{float(amount):.6f}*\n"

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        print(f"[Handler Error] /balance: {e}")
        try:
            fallback = db.reference(f"users/{user_id}/balance").get()
            fallback_balance = fallback if fallback is not None else 0.0
            await update.message.reply_text(f"💰 Legacy Balance (USD): {fallback_balance}")
        except Exception as fallback_error:
            print(f"[Fallback Error] /balance: {fallback_error}")
            await update.message.reply_text("❌ Could not fetch your balance right now.")
