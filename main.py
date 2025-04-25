from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler
import os

# Get token from environment
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TOKEN)
app = Flask(__name__)

# Dispatcher handles all updates
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)

# Commands
def start(update, context):
    update.message.reply_text("Welcome! Webhook is live and working.")

dispatcher.add_handler(CommandHandler("start", start))

# Webhook route
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# Health check
@app.route("/")
def index():
    return "Bot is running via webhook."

if __name__ == "__main__":
    app.run(port=5000)
