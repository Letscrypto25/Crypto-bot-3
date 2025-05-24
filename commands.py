import logging
from datetime import datetime
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from commands import (
    start, help_command, trade, stop_autobot,
    get_leaderboard, set_base, set_platform, set_strategy,
    set_amount, show_config
)
from database import (
    get_user_data, save_trade,
    get_user, get_all_users, firebase_ref
)
from exchanges import get_price

logger = logging.getLogger(__name__)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    firebase_ref.child(user_id).update({
        "first_name": update.message.from_user.first_name,
        "active": False,
        "autobot": False
    })
    await update.message.reply_text("Welcome! Use /register <exchange> <api_key> <secret> to begin.")

# /help
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
    await update.message.reply_text(help_text)

# /trade
async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_data = get_user_data(user_id)

    if not user_data or 'exchange' not in user_data:
        await update.message.reply_text("You're not registered. Use /register first.")
        return

    try:
        action = context.args[0].upper()
        symbol = context.args[1].upper()
        amount = float(context.args[2])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /trade <BUY/SELL> <SYMBOL> <AMOUNT>")
        return

    try:
        exchange = user_data.get("exchange")
        price = get_price(user_id=user_id, source=exchange, symbol=symbol)

        if not price:
            await update.message.reply_text("Failed to fetch price.")
            return

        trade_record = {
            "symbol": symbol,
            "amount": amount,
            "side": action,
            "price": price,
            "timestamp": datetime.utcnow().isoformat()
        }
        save_trade(user_id, trade_record)
        await update.message.reply_text(f"{action} {amount} {symbol} at {price} — Executed")

    except Exception as e:
        logger.exception("Trade error")
        await update.message.reply_text(f"Trade failed: {e}")

# /stopautobot
async def stop_autobot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.effective_user.id)
        user = get_user(user_id)
        if user:
            firebase_ref.child(user_id).update({"autobot": False})
            await update.message.reply_text("Autobot disabled.")
        else:
            await update.message.reply_text("Use /start to register.")
    except Exception as e:
        logger.exception("stop_autobot error")
        await update.message.reply_text("An error occurred while stopping the autobot.")

# /leaderboard
async def get_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        leaderboard = get_all_users()
        if leaderboard:
            sorted_users = sorted(leaderboard.items(), key=lambda x: x[1].get("total_profit", 0), reverse=True)
            message = "*Leaderboard*\n\n"
            for i, (uid, data) in enumerate(sorted_users[:10], start=1):
                name = data.get("first_name", "User")
                profit = data.get("total_profit", 0)
                message += f"{i}. {name} — ${profit:.2f}\n"
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("No users found.")
    except Exception as e:
        logger.exception("Leaderboard error")
        await update.message.reply_text("An error occurred while fetching the leaderboard.")

# /setbase
async def set_base(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.effective_user.id)
        user = get_user(user_id)
        if user and len(context.args) == 1:
            base = context.args[0].upper()
            firebase_ref.child(user_id).update({"base_currency": base})
            await update.message.reply_text(f"Base currency set to {base}.")
        else:
            await update.message.reply_text("Usage: /setbase BTC")
    except Exception as e:
        logger.exception("set_base error")
        await update.message.reply_text("An error occurred while setting base currency.")

# /setplatform
async def set_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.effective_user.id)
        user = get_user(user_id)
        if user and len(context.args) == 1:
            platform = context.args[0].lower()
            if platform in ["binance", "luno"]:
                firebase_ref.child(user_id).update({"platform": platform})
                await update.message.reply_text(f"Trading platform set to {platform}.")
            else:
                await update.message.reply_text("Supported platforms: binance, luno")
        else:
            await update.message.reply_text("Usage: /setplatform binance")
    except Exception as e:
        logger.exception("set_platform error")
        await update.message.reply_text("An error occurred while setting platform.")

# /setstrategy
async def set_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.effective_user.id)
        user = get_user(user_id)
        if user and len(context.args) == 1:
            strategy = context.args[0].lower()
            firebase_ref.child(user_id).update({"strategy": strategy})
            await update.message.reply_text(f"Strategy set to {strategy}.")
        else:
            await update.message.reply_text("Usage: /setstrategy <strategy_name>")
    except Exception as e:
        logger.exception("set_strategy error")
        await update.message.reply_text("An error occurred while setting strategy.")

# /setamount
async def set_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.effective_user.id)
        user = get_user(user_id)
        if user and len(context.args) == 1:
            try:
                amount = float(context.args[0])
                firebase_ref.child(user_id).update({"trade_amount": amount})
                await update.message.reply_text(f"Trade amount set to ${amount:.2f}.")
            except ValueError:
                await update.message.reply_text("Please enter a valid number.")
        else:
            await update.message.reply_text("Usage: /setamount 50.0")
    except Exception as e:
        logger.exception("set_amount error")
        await update.message.reply_text("An error occurred while setting amount.")

# /showconfig
async def show_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.effective_user.id)
        user_data = firebase_ref.child(user_id).get()
        if user_data:
            config_msg = (
                f"Current Config:\n"
                f"Platform: {user_data.get('platform', 'Not set')}\n"
                f"Strategy: {user_data.get('strategy', 'Not set')}\n"
                f"Trade Amount: ${user_data.get('trade_amount', 'Not set')}\n"
                f"Autobot: {'Enabled' if user_data.get('autobot', False) else 'Disabled'}\n"
                f"Status: {'Running' if user_data.get('active', False) else 'Stopped'}"
            )
            await update.message.reply_text(config_msg)
        else:
            await update.message.reply_text("No config found. Use /start to register.")
    except Exception as e:
        logger.exception("show_config error")
        await update.message.reply_text("Error fetching config.")
