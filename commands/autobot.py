import logging
from telegram import Update
from telegram.ext import ContextTypes
from firebase_admin import db

logger = logging.getLogger(__name__)

async def autobot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if len(context.args) != 1 or context.args[0].lower() not in ["enable", "disable"]:
        await update.message.reply_text("Usage: /autobot enable|disable")
        return

    action = context.args[0].lower()
    try:
        user_ref = db.reference(f"/users/{user_id}")
        user_data = user_ref.get()

        if not user_data:
            await update.message.reply_text("You're not registered yet. Use /register first.")
            return

        if action == "enable":
            user_ref.update({"autobot_enabled": True})
            await update.message.reply_text("✅ AutoBot is now *enabled* and will start trading automatically.", parse_mode="Markdown")
        elif action == "disable":
            user_ref.update({"autobot_enabled": False})
            await update.message.reply_text("🛑 AutoBot has been *disabled*. No further trades will be made automatically.", parse_mode="Markdown")

        logger.info(f"User {user_id} set AutoBot to {action.upper()}")

    except Exception as e:
        logger.exception("AutoBot toggle error")
        await update.message.reply_text("⚠️ Something went wrong while toggling AutoBot.")
