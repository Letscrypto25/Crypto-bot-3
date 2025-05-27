from telegram import Update
from telegram.ext import ContextTypes
from utils.leaderboard import get_leaderboard_data, format_leaderboard_message

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rankings = await get_leaderboard_data()
        message = format_leaderboard_message(rankings)
        await update.message.reply_text(
            message,
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"Error generating leaderboard: {e}")
