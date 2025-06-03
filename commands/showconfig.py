from telegram import Update
from telegram.ext import ContextTypes

# ⚠️ Note: These dictionaries are temporary and reset when the bot restarts.
# In production, fetch these from your database (e.g., Firebase) instead!
user_platforms = {}
user_strategies = {}
user_amounts = {}
user_bases = {}
user_autobot_status = {}

async def showconfig_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sends the user's current configuration in a single reply.
    Currently uses in-memory dictionaries (reset on restart).
    In a real app, load from persistent storage (e.g., Firebase).
    """
    user_id = update.effective_user.id

    # Get current settings or show 'Not set' if missing
    platform = user_platforms.get(user_id, "Not set")
    strategy = user_strategies.get(user_id, "Not set")
    amount = user_amounts.get(user_id, "Not set")
    base = user_bases.get(user_id, "Not set")
    autobot = user_autobot_status.get(user_id, False)  # False means disabled by default

    # Determine human-friendly status
    autobot_status = "Enabled" if autobot else "Disabled"

    # Compose the message
    msg = (
        f"🛠️ *Your current configuration:*\n\n"
        f"• *Platform:* {platform}\n"
        f"• *Strategy:* {strategy}\n"
        f"• *Trade Amount:* {amount}\n"
        f"• *Base Currency:* {base}\n"
        f"• *Autobot:* {autobot_status}"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")
