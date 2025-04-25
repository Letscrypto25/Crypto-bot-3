from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
import os
import psycopg2
import requests

# Your bot token and Render URL
TOKEN = "7874445351:AAF0pI0tuwPvTQT2wS-u8nrK96ic9opTdfY"
RENDER_URL = "https://crypto-bot-3-10.onrender.com"  # Your Render URL

bot = Bot(token=TOKEN)
app = Flask(__name__)

# Dispatcher handles all updates
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)

# Database setup for Supabase connection
DATABASE_URL = os.getenv("DATABASE_URL")  # Should be set as environment variable
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Commands
def start(update, context):
    update.message.reply_text("Welcome! Please send /id to provide your user ID.")

def id_command(update, context):
    # Get user details
    user_id = update.message.from_user.id
    username = update.message.from_user.username

    # Check if user already exists in the database
    cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (user_id,))
    user = cursor.fetchone()

    if user:
        update.message.reply_text(f"Your ID is already registered. Welcome back, {username}!")
    else:
        # Add user to the database
        cursor.execute("INSERT INTO users (telegram_id, username) VALUES (%s, %s)", (user_id, username))
        conn.commit()
        update.message.reply_text(f"Your ID has been registered. Welcome, {username}!")

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("id", id_command))

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
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
