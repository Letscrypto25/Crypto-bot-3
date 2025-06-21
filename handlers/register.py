from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref
from encryption import (
    encrypt_data,
    decrypt_data,
    hash_password,
    verify_password
)

# ✅ /register <exchange> <api_key> <secret>
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    args = context.args

    if len(args) < 3:
        await update.message.reply_text("Usage:\n`/register <exchange> <api_key> <secret>`", parse_mode="Markdown")
        return

    exchange, api_key, secret = args[:3]
    exchange = exchange.lower()

    if exchange not in ["binance", "luno"]:
        await update.message.reply_text("❌ Unsupported exchange.\nOnly `binance` and `luno` are allowed.", parse_mode="Markdown")
        return

    try:
        encrypted_key = encrypt_data(api_key)
        encrypted_secret = encrypt_data(secret)

        data = {
            "user_id": user_id,
            "username": user.username or f"user_{user_id[-4:]}",
            "exchange": exchange,
            "active": True,
            "balance": 0,
            "pnl": 0,
            "portfolio": {},
        }

        # ✅ Store exchange-specific encrypted keys
        if exchange == "binance":
            data["binance_api_key"] = encrypted_key
            data["binance_api_secret"] = encrypted_secret
        else:  # luno
            data["luno_api_key"] = encrypted_key
            data["luno_api_secret"] = encrypted_secret

        # 🔐 Log decrypted values just for dev testing (remove in production!)
        print(f"[🔐 Encrypted Key] {encrypted_key[:10]}... | [Decrypted] {decrypt_data(encrypted_key)}")
        print(f"[🔐 Encrypted Secret] {encrypted_secret[:10]}... | [Decrypted] {decrypt_data(encrypted_secret)}")

        # ✅ Save to Firebase
        firebase_ref.child(user_id).update(data)

        await update.message.reply_text(
            f"✅ Registered with *{exchange.capitalize()}*!\nYou're now active.",
            parse_mode="Markdown"
        )

    except Exception as e:
        print(f"[❌ Register Error] {e}")
        await update.message.reply_text(f"❌ Registration failed: {e}")
