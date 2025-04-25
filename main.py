import os
import requests
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler
import psycopg2
import logging

# Bot token and URL
TOKEN = "7874445351:AAF0pI0tuwPvTQT2wS-u8nrK96ic9opTdfY"
RENDER_URL = "https://crypto-bot-3-10.onrender.com"  # Your Render URL
SUPABASE_URL = "https://pqdqcthnimeurvdqpdlu.supabase.co"
SUPABASE_API_KEY = "your-supabase-api-key"

bot = Bot(token=TOKEN)
app = Flask(__name__)

# Set up Supabase database connection
def connect_db():
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="your_db_password",
        host="pqdqcthnimeurvdqpdlu.supabase.co",
        port="5432"
    )

# Dispatcher handles all updates
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)

# Commands
def start(update, context):
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    chat_id = update.message.chat_id
    user_name = update.message.from_user.full_name
    
    # Store user data in Supabase (Users table)
    conn = connect_db()
    cursor = conn.cursor()
    
    # Check if the user exists, otherwise insert new data
    cursor.execute(f"""
        INSERT INTO "Users" (telegram_id, username, full_name, chat_id)
        VALUES ('{user_id}', '{username}', '{user_name}', '{chat_id}')
        ON CONFLICT (telegram_id) DO NOTHING;
    """)
    conn.commit()
    conn.close()

    update.message.reply_text("Welcome! Your details have been saved to the database.")

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
