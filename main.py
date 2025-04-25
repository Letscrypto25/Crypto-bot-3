import os
import psycopg2
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler
import requests

# Environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

bot = Bot(token=TOKEN)
app = Flask(__name__)

# PostgreSQL DB connection
def get_db_connection():
    conn = psycopg2.connect(
        host=SUPABASE_URL.split("/")[2],
        dbname="postgres",
        user="postgres",
        password=SUPABASE_KEY,
        port=5432
    )
    return conn

# Dispatcher setup
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)

# Bot command: /start
def start(update, context):
    telegram_id = update.effective_user.id
    username = update.effective_user.username
    insert_user_data(telegram_id, username)
    update.message.reply_text("Welcome! You're now connected.")

dispatcher.add_handler(CommandHandler("start", start))

# Placeholder for future /trade command
def trade(update, context):
    update.message.reply_text("Trade feature coming soon.")

dispatcher.add_handler(CommandHandler("trade", trade))

# Webhook endpoint
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# Root route (for Render health check)
@app.route("/")
def index():
    return "Bot is running via webhook."

# Optional health check
@app.route("/health")
def health():
    return "OK", 200

# Insert user data into DB
def insert_user_data(telegram_id, username):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (telegram_id, username) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (telegram_id, username)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"DB Insert Error: {e}")

# Set Telegram webhook on app startup
def set_webhook():
    render_url = os.getenv("RENDER_EXTERNAL_URL") or "https://your-render-url.onrender.com"
    webhook_url = f"{render_url}/{TOKEN}"
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
    try:
        response = requests.get(url)
        print(response.status_code)
        print(response.json())
    except Exception as e:
        print(f"Webhook setup error: {e}")

set_webhook()

# Start app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
