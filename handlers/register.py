from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref
from encryption import ( 
    encrypt_data,
    decrypt_data, 
    hash_password, 
    verify_password
)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    args = context.args

    if len(args) < 3:
        await update.message.reply_text("Usage: /register <exchange> <api_key> <secret>")
        return

    exchange, api_key, secret = args[:3]
    exchange = exchange.lower()

    try:
        data = {
            "user_id": user_id,
            "username": user.username or f"user_{user_id[-4:]}",
            "exchange": exchange,
            "active": True,
            "balance": 0,
            "pnl": 0,
            "portfolio": {}
        }

        # Encrypt and store exchange-specific keys
        if exchange == "binance":
            data["binance_api_key"] = encrypt_data(api_key)
            data["binance_api_secret"] = encrypt_data(secret)
        elif exchange == "luno":
            data["luno_api_key"] = encrypt_data(api_key)
            data["luno_api_secret"] = encrypt_data(secret)
        else:
            await update.message.reply_text("❌ Unsupported exchange. Only 'binance' and 'luno' are supported.")
            return

        firebase_ref.child(user_id).update(data)

        await update.message.reply_text(f"✅ Registered with *{exchange.capitalize()}*! You are now active.", parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Registration failed: {e}")
