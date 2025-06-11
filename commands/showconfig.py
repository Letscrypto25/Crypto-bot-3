from telegram import Update
from telegram.ext import ContextTypes
from database import get_user_data

async def showconfig_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sends the user's current configuration fetched from Firebase.
    """
    user_id = str(update.effective_user.id)

    user_data = get_user(user_id)
    if not user_data:
        await update.message.reply_text("❌ No configuration found for your user ID.")
        return

    # Extract relevant config safely with defaults
    autobot = user_data.get("autobot", {})
    config = user_data.get("config", {})

    platform = autobot.get("platform", "Not set")
    strategy = autobot.get("strategy", "Not set")
    amount = autobot.get("amount", "Not set")
    base = autobot.get("base", "Not set")
    autobot_status = autobot.get("status", False)

    autobot_status_text = "Enabled" if autobot_status else "Disabled"

    msg = (
        f"🛠️ *Your current configuration:*\n\n"
        f"• *Platform:* {platform}\n"
        f"• *Strategy:* {strategy}\n"
        f"• *Trade Amount:* {amount}\n"
        f"• *Base Currency:* {base}\n"
        f"• *Autobot:* {autobot_status_text}"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")
