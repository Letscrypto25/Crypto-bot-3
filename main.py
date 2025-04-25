from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler
import os
import logging
import requests
from supabase import create_client, Client

# Your bot token and Render URL
TOKEN = "7874445351:AAF0pI0tuwPvTQT2wS-u8nrK96ic9opTdfY"
RENDER_URL = "https://crypto-bot-3-10.onrender.com"  # Your Render URL

# Supabase URL and API key (Replace these with your actual values)
SUPABASE_URL = "https://pqdqcthnimeurvdqpdlu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBxZHFjdGhuaW1ldXJ2ZHFwZGx1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDU1NTk1MjcsImV4cCI6MjA2MTEzNTUyN30.Rjub8T1OPZM0lgOlN57ybMvUpmyj2z8i6rokakx1sWozNTUyN30.Rjub8T1OPZM0lgOlN57ybMvUpmyj2z8i6rokakx1sWo"

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

bot = Bot(token=TOKEN)
app = Flask(__name__)

# Dispatcher handles all updates
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)

# Commands
def start(update, context):
    user_id = update.message.from_user.id  # Get user's Telegram ID
    username = update.message.from_user.username  # Get user's Telegram username
    chat_id = update.message.chat.id  # Get user's chat ID
    joined_at = update.message.date  # Get the time user joined (message date)

    # Prepare data to insert into Supabase
    data = {
        "telegram_id": str(user_id),
        "username": username,
        "joined_at": joined_at,
        "balance": 0,  # Default balance
        "profit_total": 0  # Default profit
    }

    # Insert data into the 'users' table in Supabase
    response = supabase.table('users').insert(data).execute()

    if response.status_code == 201:
        update.message.reply_text(f"Welcome {username}! Your data has been saved to the database.")
    else:
        update.message.reply_text(f"Error saving your data to the database. Please try again.")
        
# Add the '/start' command handler
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
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))  # Ensure port matches Render's environment
