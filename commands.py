# handlers.py
from telegram import Update
from telegram.ext import ContextTypes

help_text = (
    "Commands:\n"
    "/start - Welcome message\n"
    "/help - List of commands\n"
    "/register <exchange> <api_key> <api_secret> - Register your API keys\n"
    "/balance - Show your current balance\n"
    "/trade <BUY/SELL> <symbol> <amount> - Execute a trade\n"
    "/leaderboard - Show top traders\n"
    "/autobot enable|disable - Enable or disable auto trading\n"
    "/autobot config <key> <value> - Configure auto bot parameters\n"
)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /help to see available commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(help_text)

