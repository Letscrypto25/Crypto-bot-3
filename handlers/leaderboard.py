# handlers/leaderboard.py

from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref

async def get_leaderboard_data(top_n=10):
    all_users = firebase_ref.get()
    if not all_users:
        return []

    rankings = []
    for uid, data in all_users.items():
        pnl = float(data.get("pnl", 0))
        username = data.get("username") or uid[:6]
        rankings.append((username, pnl))

    rankings.sort(key=lambda x: x[1], reverse=True)
    return rankings[:top_n]

def format_leaderboard_message(rankings):
    if not rankings:
        return "No user data or PnL data available."

    msg_lines = ["*Leaderboard (Top 10)*\n"]
    for i, (username, pnl) in enumerate(rankings, start=1):
        msg_lines.append(f"{i}. `{username}`: *${pnl:,.2f}*")

    return "\n".join(msg_lines)

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
