# commands.py
import os
import requests
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from database import get_user_data, update_user_data, save_trade, get_leaderboard_ref, get_trades_ref
from exchanges import get_binance_client, get_luno_auth
from tasks import send_telegram_message, update_leaderboard

logger = logging.getLogger(__name__)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /register to begin.")

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "/register <exchange> <api_key> <secret>\n"
        "/balance - Check your balance\n"
        "/trade BUY/SELL SYMBOL AMOUNT\n"
        "/leaderboard - Show top profits\n"
        "/autobot enable|disable\n"
        "/autobot_config key value"
    )
    await update.message.reply_text(help_text)

# /trade
async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if 'exchange' not in user_data:
        await update.message.reply_text("You're not registered. Use /register first.")
        return

    try:
        action, symbol, amount = context.args[0].upper(), context.args[1].upper(), float(context.args[2])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /trade <BUY/SELL> <SYMBOL> <AMOUNT>")
        return

    try:
        price = None
        if user_data['exchange'] == 'binance':
            client = get_binance_client(user_data)
            if action == "BUY":
                order = client.order_market_buy(symbol=symbol, quantity=amount)
            elif action == "SELL":
                order = client.order_market_sell(symbol=symbol, quantity=amount)
            else:
                await update.message.reply_text("Action must be BUY or SELL.")
                return
            price = order['fills'][0]['price']

        elif user_data['exchange'] == 'luno':
            market = symbol.lower()
            url = "https://api.luno.com/api/1/marketorder"
            side = "BUY" if action == "BUY" else "SELL"
            data = {"pair": market, "type": side.lower(), "counter_volume": str(amount)}
            resp = requests.post(url, auth=get_luno_auth(user_data), data=data)
            result = resp.json()
            if resp.status_code != 200:
                await update.message.reply_text(f"Luno API error: {result.get('error_message', resp.text)}")
                return
            price = result.get("average_price") or "unknown"

        else:
            await update.message.reply_text("Exchange not recognized.")
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

    try:
    # Your main code here
    # for example, check if user exists
        if user:
        # do something
        await update.message.reply_text("Trade executed")
    else:
        await update.message.reply_text("You need to verify your account with /start before using this bot.")
except Exception as e:
    logger.exception("Trade error")
    await update.message.reply_text(f"Trade failed: {e}")
def stop_autobot(update: Update, context: CallbackContext) -> None:
    try:
        user_id = str(update.effective_user.id)
        user = get_user(user_id)
        if user:
            firebase_ref.child(user_id).update({"autobot": False})
            update.message.reply_text("Autobot disabled.")
        else:
            update.message.reply_text("You need to verify your account with /start before using this bot.")
    except Exception as e:
        print(f"Error in /stopautobot command: {e}")
        update.message.reply_text("An error occurred while stopping the autobot.")

def get_leaderboard(update: Update, context: CallbackContext) -> None:
    try:
        leaderboard = get_all_users()
        if leaderboard:
            sorted_users = sorted(
                leaderboard.items(), key=lambda x: x[1].get("total_profit", 0), reverse=True
            )
            message = "*Leaderboard*\n\n"
            for i, (uid, data) in enumerate(sorted_users[:10], start=1):
                message += f"{i}. {data.get('first_name', 'User')} — ${data.get('total_profit', 0):.2f}\n"
            update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        else:
            update.message.reply_text("No users found.")
    except Exception as e:
        print(f"Error in /leaderboard command: {e}")
        update.message.reply_text("An error occurred while fetching the leaderboard.")

def set_base(update: Update, context: CallbackContext) -> None:
    try:
        user_id = str(update.effective_user.id)
        user = get_user(user_id)
        if user:
            if len(context.args) == 1:
                base = context.args[0].upper()
                firebase_ref.child(user_id).update({"base_currency": base})
                update.message.reply_text(f"Base currency set to {base}.")
            else:
                update.message.reply_text("Usage: /setbase BTC")
        else:
            update.message.reply_text("You need to verify your account with /start before using this bot.")
    except Exception as e:
        print(f"Error in /setbase command: {e}")
        
        update.message.reply_text("An error occurred while setting base currency.")
def set_platform(update: Update, context: CallbackContext) -> None:
    try:
        user_id = str(update.effective_user.id)
        user = get_user(user_id)
        if user:
            if len(context.args) == 1:
                platform = context.args[0].lower()
                if platform in ["binance", "luno"]:
                    firebase_ref.child(user_id).update({"platform": platform})
                    update.message.reply_text(f"Trading platform set to {platform}.")
                else:
                    update.message.reply_text("Supported platforms: binance, luno")
            else:
                update.message.reply_text("Usage: /setplatform binance")
        else:
            update.message.reply_text("You need to verify your account with /start before using this bot.")
    except Exception as e:
        print(f"Error in /setplatform command: {e}")
        update.message.reply_text("An error occurred while setting platform.")

def set_strategy(update: Update, context: CallbackContext) -> None:
    try:
        user_id = str(update.effective_user.id)
        user = get_user(user_id)
        if user:
            if len(context.args) == 1:
                strategy = context.args[0].lower()
                firebase_ref.child(user_id).update({"strategy": strategy})
                update.message.reply_text(f"Strategy set to {strategy}.")
            else:
                update.message.reply_text("Usage: /setstrategy <strategy_name>")
        else:
            update.message.reply_text("You need to verify your account with /start before using this bot.")
    except Exception as e:
        print(f"Error in /setstrategy command: {e}")
        update.message.reply_text("An error occurred while setting strategy.")

def set_amount(update: Update, context: CallbackContext) -> None:
    try:
        user_id = str(update.effective_user.id)
        user = get_user(user_id)
        if user:
            if len(context.args) == 1:
                try:
                    amount = float(context.args[0])
                    firebase_ref.child(user_id).update({"trade_amount": amount})
                    update.message.reply_text(f"Trade amount set to ${amount:.2f}.")
                except ValueError:
                    update.message.reply_text("Please enter a valid number.")
            else:
                update.message.reply_text("Usage: /setamount 50.0")
        else:
            update.message.reply_text("You need to verify your account with /start before using this bot.")
    except Exception as e:
        print(f"Error in /setamount command: {e}")
        update.message.reply_text("An error occurred while setting amount.")

def show_config(update: Update, context: CallbackContext) -> None:
    try:
        user_id = str(update.effective_user.id)
        user_data = firebase_ref.child(user_id).get()
        if user_data:
            config_msg = (
                f"Current Config:\n"
                f"Platform: {user_data.get('platform', 'Not set')}\n"
                f"Strategy: {user_data.get('strategy', 'Not set')}\n"
                f"Trade Amount: ${user_data.get('trade_amount', 'Not set')}\n"
                f"Status: {'Running' if user_data.get('active', False) else 'Stopped'}"
            )
            update.message.reply_text(config_msg)
        else:
            update.message.reply_text("No config found. Use /start to register.")
    except Exception as e:
        print(f"Error in /showconfig: {e}")
        update.message.reply_text("Error fetching config.")

def show_help(update: Update, context: CallbackContext) -> None:
    help_text = (
        "Available Commands:\n"
        "/start - Verify and activate your account\n"
        "/stop - Stop the bot\n"
        "/startbot - Start the trading bot\n"
        "/setplatform <binance|luno> - Set your exchange platform\n"
        "/setstrategy <strategy_name> - Set trading strategy\n"
        "/setamount <amount> - Set trade amount in USD\n"
        "/status - Check bot status\n"
        "/showconfig - View current configuration\n"
        "/help - Show this message"
    )
    update.message.reply_text(help_text)

# END OF COMMANDS MODULE
