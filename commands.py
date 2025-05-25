import os
import logging
import json
import base64
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request
import requests
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext, ApplicationBuilder

# Firebase initialization
with open("firebase_encoded.txt", "r") as f:
    encoded = f.read()
cred = credentials.Certificate(json.loads(base64.b64decode(encoded)))
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://cryptotest-dc7f0-default-rtdb.firebaseio.com/'
})

token = os.environ.get("BOT_TOKEN")
OWNER_ID = os.environ.get("OWNER_ID")
app = Flask(__name__)

async def start(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    ref = db.reference(f"users/{user_id}")
    if not ref.get():
        ref.set({
            'name': update.effective_user.first_name,
            'active': False,
            'autobot': False,
            'total_profit': 0
        })
    await update.message.reply_text("Welcome! Use /register <exchange> <api_key> <secret> to begin.")

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text("""
/start - Start the bot
/help - Show this help message
/register <exchange> <api_key> <secret>
/setplatform <binance|luno>
/setstrategy <strategy_name>
/setamount <amount>
/setbase <currency>
/trade <BUY/SELL> <SYMBOL> <AMOUNT>
/balance - Get your exchange balance
/autobot enable|disable
/autobot_config <key> <value>
/showconfig - Show your bot settings
/leaderboard - Show top users
/stopautobot - Disable your trading bot
""")

async def register(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /register <exchange> <api_key> <secret>")
        return
    exchange, api_key, api_secret = context.args
    ref = db.reference(f"users/{user_id}")
    ref.update({
        'exchange': exchange,
        'api_key': api_key,
        'api_secret': api_secret
    })
    await update.message.reply_text(f"Exchange credentials saved for {exchange}.")

async def balance(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    user_data = db.reference(f"users/{user_id}").get()
    if not user_data or 'exchange' not in user_data:
        await update.message.reply_text("Please register your exchange first using /register.")
        return
    if user_data['exchange'] == 'binance':
        client = BinanceClient(user_data['api_key'], user_data['api_secret'])
        try:
            account_info = client.get_account()
            balances = [b for b in account_info['balances'] if float(b['free']) > 0]
            message = "Your balances:\n" + "\n".join([f"{b['asset']}: {b['free']}" for b in balances])
        except BinanceAPIException as e:
            message = f"Error fetching balance: {e.message}"
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("Exchange not supported yet.")

async def autobot_config(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /autobot_config <key> <value>")
        return
    key, value = context.args
    ref = db.reference(f"users/{user_id}/autobot_config")
    ref.update({key: value})
    await update.message.reply_text(f"Autobot config updated: {key} = {value}")

async def autobot(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if not context.args or context.args[0] not in ['enable', 'disable']:
        await update.message.reply_text("Usage: /autobot enable|disable")
        return
    enable = context.args[0] == 'enable'
    db.reference(f"users/{user_id}").update({'autobot': enable})
    await update.message.reply_text(f"Autobot {'enabled' if enable else 'disabled'}.")

async def setplatform(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Please specify a platform: binance or luno")
        return
    platform = context.args[0].lower()
    if platform in ['binance', 'luno']:
        db.reference(f"users/{user_id}").update({'platform': platform})
        await update.message.reply_text(f"Platform set to {platform}.")
    else:
        await update.message.reply_text("Unsupported platform.")

async def setstrategy(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Please provide a strategy name.")
        return
    strategy = context.args[0]
    db.reference(f"users/{user_id}").update({'strategy': strategy})
    await update.message.reply_text(f"Strategy set to {strategy}.")

async def setamount(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    try:
        amount = float(context.args[0])
        db.reference(f"users/{user_id}").update({'trade_amount': amount})
        await update.message.reply_text(f"Trade amount set to {amount}.")
    except (ValueError, IndexError):
        await update.message.reply_text("Usage: /setamount <amount>")

async def setbase(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Please provide a base currency.")
        return
    base_currency = context.args[0]
    db.reference(f"users/{user_id}").update({'base_currency': base_currency})
    await update.message.reply_text(f"Base currency set to {base_currency}.")

async def showconfig(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    user_data = db.reference(f"users/{user_id}").get()
    if not user_data:
        await update.message.reply_text("User not registered.")
        return
    config = "\n".join([f"{k}: {v}" for k, v in user_data.items()])
    await update.message.reply_text(f"Your configuration:\n{config}")

async def stopautobot(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    db.reference(f"users/{user_id}").update({'autobot': False})
    await update.message.reply_text("Autobot stopped.")

async def leaderboard(update: Update, context: CallbackContext):
    all_users = db.reference("users").get()
    if not all_users:
        await update.message.reply_text("No users found.")
        return
    sorted_users = sorted(all_users.items(), key=lambda x: x[1].get('total_profit', 0), reverse=True)[:10]
    leaderboard_text = "Leaderboard:\n"
    for i, (uid, data) in enumerate(sorted_users, 1):
        leaderboard_text += f"{i}. {data.get('name', 'Anonymous')} - Profit: {data.get('total_profit', 0)}\n"
    await update.message.reply_text(leaderboard_text)

async def trade(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /trade <BUY/SELL> <SYMBOL> <AMOUNT>")
        return
    direction, symbol, amount = context.args
    amount = float(amount)
    user_data = db.reference(f"users/{user_id}").get()
    if not user_data:
        await update.message.reply_text("User not found. Use /start first.")
        return
    price = 100.0  # Replace with real-time price fetch
    trade_data = {
        'direction': direction,
        'symbol': symbol,
        'amount': amount,
        'price': price
    }
    db.reference(f"users/{user_id}/trades").push(trade_data)
    await update.message.reply_text(f"Trade executed: {direction} {amount} {symbol} at ${price}")

application = ApplicationBuilder().token(token).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("register", register))
application.add_handler(CommandHandler("balance", balance))
application.add_handler(CommandHandler("autobot_config", autobot_config))
application.add_handler(CommandHandler("autobot", autobot))
application.add_handler(CommandHandler("setplatform", setplatform))
application.add_handler(CommandHandler("setstrategy", setstrategy))
application.add_handler(CommandHandler("setamount", setamount))
application.add_handler(CommandHandler("setbase", setbase))
application.add_handler(CommandHandler("showconfig", showconfig))
application.add_handler(CommandHandler("stopautobot", stopautobot))
application.add_handler(CommandHandler("leaderboard", leaderboard))
application.add_handler(CommandHandler("trade", trade))
