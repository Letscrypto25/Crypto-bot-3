from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database import get_user_data

WELCOME_MESSAGE = """
🌿 *Welcome to CryptoBot* 🌿

Hi {name}, great to have you here! 👋  
This bot helps you track your crypto balances, run auto-trading bots, and more — directly from Telegram.

Here's what you can do:
• 💰 `/balance` — Check your current balances  
• 🤖 `/autobot` — Enable or disable the auto trader  
• 🔐 `/register` — Link your exchange account  
• 📊 `/price BTCUSDT` — Check a price quickly  

_You're all set. Let's grow your crypto journey together! 🚀_
"""

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)

    # Check if user is registered already
    user_data = get_user_data(user_id)
    is_registered = bool(user_data and user_data.get("exchange"))

    extra_note = "\n\n✅ You're already registered!" if is_registered else "\n\n❗Use /register to get started."

    welcome_text = WELCOME_MESSAGE.format(name=user.first_name or "there") + extra_note
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
