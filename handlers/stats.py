# handlers/stats.py

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database import firebase_ref

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = firebase_ref.child(user_id).get()

    if not user_data:
        await update.message.reply_text("No stats found. Make a trade first.")
        return

    balance = float(user_data.get("balance", 0))
    pnl = float(user_data.get("pnl", 0))
    trades = int(user_data.get("trades", 0))
    wins = int(user_data.get("wins", 0))
    losses = int(user_data.get("losses", 0))

    win_rate = (wins / trades * 100) if trades > 0 else 0.0

    msg = (
        f"*Your Stats:*\n"
        f"`Balance:` ${balance:.2f}\n"
        f"`PnL:` ${pnl:.2f}\n"
        f"`Trades:` {trades}\n"
        f"`Wins:` {wins}\n"
        f"`Losses:` {losses}\n"
        f"`Win Rate:` {win_rate:.1f}%"
    )

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
