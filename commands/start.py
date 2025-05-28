import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref

logger = logging.getLogger(__name__)
last_message_ids = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    msg_id = update.message.message_id

    if last_message_ids.get(user_id) == msg_id:
        return
    last_message_ids[user_id] = msg_id

    user_data = firebase_ref.child(user_id).get()

    if not user_data:
        firebase_ref.child(user_id).set({
            "first_name": update.message.from_user.first_name,
            "active": False,
            "autobot": False
        })
        await update.message.reply_text("Welcome to LET'SCRYPTO! Use /register <exchange> <api_key> <secret> to begin.")
    else:
        await update.message.reply_text("You’re already registered. Use /help to see what you can do.")
