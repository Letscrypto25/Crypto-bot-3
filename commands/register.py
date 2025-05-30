import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref
From encryption import ( 
    encrypt_data,
    decrypt_data,
    hash_password,
    verify_password
)
logger = logging.getLogger(__name__)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    try:
        if len(context.args) != 3:
            await update.message.reply_text("Usage: /register <exchange> <api_key> <secret>")
            return

        exchange, api_key, secret = context.args
        firebase_ref.child(user_id).update({
            "exchange": exchange.lower(),
            "api_key": api_key,
            "secret": secret
        })
        await update.message.reply_text("Registered successfully with your exchange details.")
    except Exception as e:
        logger.exception("register error")
        await update.message.reply_text("An error occurred during registration.")
