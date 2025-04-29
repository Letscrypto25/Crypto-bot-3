import os
import psycopg2
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler
import requests
import random
import time

# Load environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
RAILWAY_URL = os.getenv("RAILWAY_STATIC_URL")  # For webhook

bot = Bot(token=TOKEN)
app = Flask(__name__)

# Connect to Supabase PostgreSQL
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=SUPABASE_URL.split("/")[2],
            dbname="postgres",
            user="postgres",
            password=SUPABASE_KEY,
            port=5432,
            connect_timeout=5
        )
        return conn
    except Exception as e:
        print(f"Database error: {e}")
        return None

dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)

# /start command
def start(update, context):
    telegram_id = update.message.chat_id
    username = update.message.chat.username
    conn = get_db_connection()
    if not conn:
        update.message.reply_text("Database connection failed.")
        return
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO "Users" (telegram_id, username)
        VALUES (%s, %s)
        ON CONFLICT (telegram_id) DO NOTHING
    """, (telegram_id, username))
    conn.commit()
    cursor.close()
    conn.close()
    update.message.reply_text("Welcome! You're now set up.")

# /trade command
def trade(update, context):
    conn = get_db_connection()
    if not conn:
        update.message.reply_text("Database connection failed.")
        return
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM "Users" ORDER BY RANDOM() LIMIT 1;')
    user = cursor.fetchone()
    if not user:
        update.message.reply_text("No users found. Use /start first.")
        return
    user_id = user[0]
    cursor.execute("""
        INSERT INTO "Trades" (user_id, platform, coin, amount, buy_price, sell_price, profit, status, strategy)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (user_id, 'Binance', 'BTC', 0.001, 60000, 60200, 2, 'completed', 'arbitrage'))
    conn.commit()
    cursor.close()
    conn.close()
    update.message.reply_text("Trade inserted!")

# /log_trade command
def log_trade(update, context):
    conn = get_db_connection()
    if not conn:
        update.message.reply_text("Database connection failed.")
        return
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM "Trades" ORDER BY RANDOM() LIMIT 1;')
    trade = cursor.fetchone()
    if not trade:
        update.message.reply_text("No trades found. Use /trade first.")
        return
    trade_id = trade[0]
    cursor.execute("""
        INSERT INTO "TradeLogs" (trade_id, time_taken, fee, comment)
        VALUES (%s, %s, %s, %s)
    """, (trade_id, random.randint(1, 5), round(random.uniform(0.1, 1.0), 2), "Test log"))
    conn.commit()
    cursor.close()
    conn.close()
    update.message.reply_text("Trade log inserted!")

# Add command handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("trade", trade))
dispatcher.add_handler(CommandHandler("log_trade", log_trade))

# Telegram webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
        return "ok", 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return "error", 500

@app.route("/")
def index():
    return "Bot running."

def set_webhook():
    if RAILWAY_URL:
        webhook_url = f"{RAILWAY_URL}/{TOKEN}"
        url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
        response = requests.get(url)
        print(f"Webhook response: {response.status_code}")
        print(response.json())
    else:
        print("RAILWAY_STATIC_URL not found.")

set_webhook()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
