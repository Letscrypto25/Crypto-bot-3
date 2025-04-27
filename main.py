import os
import psycopg2
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler
import requests
import random

# Load environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
RENDER_URL = os.getenv("RENDER_URL")

bot = Bot(token=TOKEN)
app = Flask(__name__)

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=SUPABASE_URL.split("/")[2],
            dbname="postgres",
            user="postgres",
            password=SUPABASE_KEY,
            port=5432
        )
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)

# /start command
def start(update, context):
    telegram_id = update.message.chat_id
    username = update.message.chat.username
    conn = get_db_connection()

    if not conn:
        update.message.reply_text("Error connecting to the database.")
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
    update.message.reply_text("Welcome! Your account is set up.")

# /trade command
def trade(update, context):
    conn = get_db_connection()

    if not conn:
        update.message.reply_text("Error connecting to the database.")
        return

    cursor = conn.cursor()

    # Randomly pick a User
    cursor.execute('SELECT id FROM "Users" ORDER BY RANDOM() LIMIT 1;')
    user = cursor.fetchone()

    if not user:
        update.message.reply_text("No users found. Please /start first.")
        return

    user_id = user[0]

    # Insert a fake trade
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
        update.message.reply_text("Error connecting to the database.")
        return

    cursor = conn.cursor()

    cursor.execute('SELECT id FROM "Trades" ORDER BY RANDOM() LIMIT 1;')
    trade = cursor.fetchone()

    if not trade:
        update.message.reply_text("No trades to log. Insert a trade first.")
        return

    trade_id = trade[0]

    # Insert a trade log
    cursor.execute("""
        INSERT INTO "TradeLogs" (trade_id, time_taken, fee, comment)
        VALUES (%s, %s, %s, %s)
    """, (trade_id, random.randint(1, 5), random.uniform(0.1, 1.0), "Test log"))

    conn.commit()
    cursor.close()
    conn.close()
    update.message.reply_text("Trade log inserted!")

# Dispatcher handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("trade", trade))
dispatcher.add_handler(CommandHandler("log_trade", log_trade))

# Modify webhook handler to quickly respond and prevent timeouts
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
        return "ok", 200  # Fast response to avoid worker timeouts
    except Exception as e:
        print(f"Error processing update: {e}")
        return "error", 500

@app.route("/")
def index():
    return "Bot is running."

def set_webhook():
    webhook_url = f"{RENDER_URL}/{TOKEN}"
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
    response = requests.get(url)
    print(response.status_code)
    print(response.json())

set_webhook()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
