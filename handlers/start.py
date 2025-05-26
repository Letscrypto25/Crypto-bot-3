# handlers/start.py

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database import firebase_ref

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)

    firebase_ref.child(user_id).update({
        "first_name": user.first_name,
        "username": user.username or f"user_{user_id[-4:]}",
        "active": False,
        "autobot": False,
    })

    await update.message.reply_text(
        f"Welcome {user.first_name}! Use /register <exchange> <api_key> <secret> to begin."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "*Available Commands:*\n"
        "`/start` - Verify and activate your account\n"
        "`/register <exchange> <api_key> <secret>` - Register your trading account\n"
        "`/balance` - Check your balance\n"
        "`/trade <BUY/SELL> <SYMBOL> <AMOUNT>` - Execute a trade\n"
        "`/autobot enable|disable` - Toggle auto trading\n"
        "`/autobot_config <key> <value>` - Configure autobot settings\n"
        "`/leaderboard` - Show top profits\n"
        "`/setplatform <binance|luno>` - Set your preferred exchange\n"
        "`/setstrategy <strategy_name>` - Choose your trading strategy\n"
        "`/setamount <amount>` - Set trade size\n"
        "`/setbase <currency>` - Set base currency\n"
        "`/showconfig` - View current autobot config\n"
        "`/help` - Show this help message"
    )

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
