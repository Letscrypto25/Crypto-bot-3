from telegram import Update
from telegram.ext import ContextTypes

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Available Commands:\n"
        "/start - Verify and activate your account\n"
        "/register -  add you LUNO/BINANCE API here in the following order. <exchange> <api_key> <secret>\n"
        "/balance - Check your balance\n"
        "/trade - for quick trade on the go.<BUY/SELL> <SYMBOL> <AMOUNT>\n"
        "/autobot enable|disable your bot once configured.\n"
        "/autobot_config <key> <value>\n"
        "/leaderboard - Show top profits\n"
        "/setplatform <choose between Luno or Binance>\n"
        "/setstrategy <strategy_name>\n"
        "/setamount <choose amountper trade>\n"
        "/setbase <choose what coin to trade with>\n"
        "/showconfig - View current configuration\n"
        "/help - Show this message"
    )
    await update.message.reply_text(help_text)
