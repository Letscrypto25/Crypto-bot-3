from telegram import Update
from telegram.ext import ContextTypes
from firebase_admin import db

async def setplatform_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args

    if not args:
        await update.message.reply_text("Usage: /setplatform <binance|luno>")
        return

    platform = args[0].lower()

    if platform not in ("binance", "luno"):
        await update.message.reply_text("Invalid platform. Choose 'binance' or 'luno'.")
        return

    # Save platform to Firebase
    db.reference(f"/users/{user_id}/settings").update({"platform": platform})

    await update.message.reply_text(f"✅ Platform saved to cloud: {platform}")
