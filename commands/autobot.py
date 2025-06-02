# commands/autobot.py

from telegram import Update
from telegram.ext import ContextTypes
from database import get_autobot_status, set_autobot_status
from utils import send_alert
from firebase_admin import db

def migrate_keys(user_id):
    # Optional: any logic you want for migrating keys or updating structure
    pass

async def autobot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id

    migrate_keys(user_id)

    try:
        current_status = get_autobot_status(user_id)
        new_status = not current_status

        set_autobot_status(user_id, new_status)

        if new_status:
            send_alert("✅ AutoBot started. It will trade based on your config.", chat_id)
        else:
            send_alert("🛑 AutoBot stopped.", chat_id)

        log_ref = db.reference(f"logs/{user_id}")
        log_ref.push({
            "timestamp": update.effective_message.date.isoformat(),
            "event": "autobot_toggle",
            "status": "on" if new_status else "off"
        })

    except Exception as e:
        send_alert(f"⚠️ Error toggling AutoBot: {e}", chat_id)
