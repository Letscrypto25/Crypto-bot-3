from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref

last_message_ids = {}

async def autobot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    msg_id = update.message.message_id

    # Prevent duplicate processing
    if last_message_ids.get(user_id) == msg_id:
        return
    last_message_ids[user_id] = msg_id

    args = context.args
    if len(args) != 1 or args[0].lower() not in ["enable", "disable"]:
        await update.message.reply_text("Usage: /autobot enable|disable")
        return

    status = args[0].lower()
    try:
        # Save the autobot status in Firebase under user config
        user_config_ref = firebase_ref.child("users").child(user_id).child("config")
        user_config_ref.update({"autobot": status})

        await update.message.reply_text(f"Autobot has been {status}d.")
    except Exception as e:
        await update.message.reply_text(f"Error updating autobot status: {e}")
