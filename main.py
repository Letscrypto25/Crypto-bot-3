import os
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters

TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=TOKEN)

app = Flask(__name__)

# Setup dispatcher
dispatcher = Dispatcher(bot, None, workers=0)

# --- Command Handlers ---

def start(update: Update, context):
    update.message.reply_text("Welcome! This bot is running via webhook on Fly.io.")

def help_command(update: Update, context):
    update.message.reply_text("Available commands:\n/start\n/help\n/balance")

def balance(update: Update, context):
    # Dummy balance
    update.message.reply_text("Your current balance is R500.")

def unknown(update: Update, context):
    update.message.reply_text("Sorry, I didn't understand that command.")

# Register handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(CommandHandler("balance", balance))
dispatcher.add_handler(MessageHandler(filters.COMMAND, unknown))

# --- Webhook Route ---

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok", 200

@app.route("/", methods=["GET"])
def home():
    return "Telegram bot is running via webhook!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
