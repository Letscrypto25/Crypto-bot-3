# handlers/start.py

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database import firebase_ref

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = str(user.id)
    firebase_ref.child(user_id).update({
        "first_name": user.first_name,
        "active": False,
        "autobot": False
    })
    await update.message.reply_text(f"Welcome {user.first_name}! Use /register <exchange> <api_key> <secret> to begin.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Available Commands:\n"
        "/start - Verify and activate your account\n"
        "/register <exchange> <api_key> <secret>\n"
        "/balance - Check your balance\n"
        "/trade <BUY/SELL> <SYMBOL> <AMOUNT>\n"
        "/autobot enable|disable\n"
        "/autobot_config <key> <value>\n"
        "/leaderboard - Show top profits\n"
        "/setplatform <binance|luno>\n"
        "/setstrategy <strategy_name>\n"
        "/setamount <amount>\n"
        "/setbase <currency>\n"
        "/showconfig - View current configuration\n"
        "/help - Show this message"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
