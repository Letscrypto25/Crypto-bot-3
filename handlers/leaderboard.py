# handlers/leaderboard.py

from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        all_users = firebase_ref.get()
        if not all_users:
            await update.message.reply_text("No user data found.")
            return

        # Create leaderboard data
        rankings = []
        for uid, data in all_users.items():
            pnl = float(data.get("pnl", 0))
            username = data.get("username") or uid[:6]
            rankings.append((username, pnl))

        if not rankings:
            await update.message.reply_text("No PnL data available.")
            return

        # Sort by PnL descending
        rankings.sort(key=lambda x: x[1], reverse=True)

        # Format message
        msg_lines = ["*Leaderboard (Top 10)*\n"]
        for i, (username, pnl) in enumerate(rankings[:10], start=1):
            msg_lines.append(f"{i}. `{username}`: *${pnl:,.2f}*")

        await update.message.reply_text(
            "\n".join(msg_lines),
            parse_mode="Markdown"
        )

    except Exception as e:
        await update.message.reply_text(f"Error generating leaderboard: {e}")
