# handlers/leaderboard.py

from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_users = firebase_ref.get()
    if not all_users:
        await update.message.reply_text("No user data found.")
        return

    rankings = []
    for uid, data in all_users.items():
        pnl = float(data.get("pnl", 0))
        username = data.get("username", uid)
        rankings.append((username, pnl))

    rankings.sort(key=lambda x: x[1], reverse=True)

    msg = "*Leaderboard:*\n"
    for i, (username, pnl) in enumerate(rankings[:10], start=1):
        msg += f"{i}. {username}: ${pnl:.2f}\n"

    await update.message.reply_text(msg, parse_mode="Markdown")
