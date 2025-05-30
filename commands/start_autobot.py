from telegram import Update
from telegram.ext import ContextTypes
from utils import send_alert
from auto_bot import run_auto_bot
from database import get_user
from firebase_admin import db

async def start_autobot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_chat.id)

    user = get_user(user_id)
    if not user:
        await send_alert("You are not registered. Use /register first.", user_id)
        return

    # Optional: mark in Firebase that autobot is active
    try:
        db.reference(f"users/{user_id}/autobot_active").set(True)
    except Exception as e:
        await send_alert(f"Failed to set autobot status: {e}", user_id)

    try:
        await send_alert("🚀 Starting AutoBot...", user_id)
        await run_auto_bot(user_id)
        await send_alert("✅ AutoBot started!", user_id)
    except Exception as e:
        await send_alert(f"❌ AutoBot error: {e}", user_id)
