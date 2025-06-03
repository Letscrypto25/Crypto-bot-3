from telegram import Update
from telegram.ext import ContextTypes

# Store user platform selection here, replace with DB for real app
user_platforms = {}

async def setplatform_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if not args:
        await update.message.reply_text("Usage: /setplatform <binance|luno>")
        return

    platform = args[0].lower()

    if platform not in ("binance", "luno"):
        await update.message.reply_text("Invalid platform. Choose 'binance' or 'luno'.")
        return

    user_platforms[user_id] = platform
    await update.message.reply_text(f"✅ Platform set to: `{platform}`", parse_mode="Markdown")
