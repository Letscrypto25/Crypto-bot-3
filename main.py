from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler
import os
import logging
import psycopg2
import requests

# Your bot token and Render URL
TOKEN = "7874445351:AAF0pI0tuwPvTQT2wS-u8nrK96ic9opTdfY"
RENDER_URL = "https://crypto-bot-3-10.onrender.com"  # Your Render URL

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

# Health check route for Render to ensure it's working
@app.route("/")
def index():
    return "Bot is running via webhook."

# Set webhook function
def set_webhook():
    webhook_url = f"{RENDER_URL}/{TOKEN}"
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
    response = requests.get(url)
    print(response.status_code)
    print(response.json())

# Set the webhook when the app starts
set_webhook()

if __name__ == "__main__":
    # Disable debug mode and ensure the app runs with Gunicorn in production
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))  # Ensure port matches Render's environment
