from telegram import Update
from telegram.ext import ContextTypes
from database import firebase_ref

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        users_ref = firebase_ref.child("users")
        users_snapshot = users_ref.get()

        if not users_snapshot:
            await update.message.reply_text("No data available for leaderboard.")
            return

        leaderboard_data = []
        for uid, data in users_snapshot.items():
            username = data.get("username", "Unknown")
            profit = float(data.get("profit", 0))
            initial_investment = float(data.get("initial_investment", 0))

            if initial_investment > 0:
                profit_percent = (profit / initial_investment) * 100
            else:
                profit_percent = 0

            leaderboard_data.append((username, profit_percent))

        top_users = sorted(leaderboard_data, key=lambda x: x[1], reverse=True)[:10]

        if not top_users:
            await update.message.reply_text("No leaderboard data found.")
            return

        leaderboard_text = "🏆 Top Profits Percentage Leaderboard:\n"
        for i, (username, profit_percent) in enumerate(top_users, start=1):
            leaderboard_text += f"{i}. {username}: {profit_percent:.2f}%\n"

        await update.message.reply_text(leaderboard_text)

    except Exception as e:
        await update.message.reply_text(f"Error fetching leaderboard: {e}") 
