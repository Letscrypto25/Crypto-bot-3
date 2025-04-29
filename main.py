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
RENDER_URL = os.getenv("RENDER_URL")

bot = Bot(token=TOKEN)
app = Flask(__name__)

# Database connection
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
        print(f"Error connecting to database: {e}")
        return None

dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)

# USD to ZAR converter
def usd_to_zar(amount_usd):
    try:
        response = requests.get('https://api.exchangerate.host/latest?base=USD&symbols=ZAR')
        data = response.json()
        rate = data['rates']['ZAR']
        return round(amount_usd * rate, 2)
    except Exception as e:
        print(f"Error fetching exchange rate: {e}")
        return None

# /start command
def start(update, context):
    telegram_id = update.message.chat_id
    username = update.message.chat.username
    conn = get_db_connection()
    if not conn:
        update.message.reply_text("Failed to connect to the database.")
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
        update.message.reply_text("Failed to connect to the database.")
        return

    cursor = conn.cursor()
    start_time = time.time()
    cursor.execute('SELECT id FROM "Users" ORDER BY RANDOM() LIMIT 1;')
    print(f"Query execution time for random user fetch: {time.time() - start_time} seconds")
    user = cursor.fetchone()

    if not user:
        update.message.reply_text("No users found. Please /start first.")
        return

    user_id = user[0]

    start_time = time.time()
    cursor.execute("""
        INSERT INTO "Trades" (user_id, platform, coin, amount, buy_price, sell_price, profit, status, strategy)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (user_id, 'Binance', 'BTC', 0.001, 60000, 60200, 2, 'completed', 'arbitrage'))
    print(f"Query execution time for inserting trade: {time.time() - start_time} seconds")

    conn.commit()
    cursor.close()
    conn.close()
    update.message.reply_text("Trade inserted!")

# /log_trade command
def log_trade(update, context):
    conn = get_db_connection()
    if not conn:
        update.message.reply_text("Failed to connect to the database.")
        return

    cursor = conn.cursor()
    start_time = time.time()
    cursor.execute('SELECT id FROM "Trades" ORDER BY RANDOM() LIMIT 1;')
    print(f"Query execution time for random trade fetch: {time.time() - start_time} seconds")
    trade = cursor.fetchone()

    if not trade:
        update.message.reply_text("No trades to log. Insert a trade first.")
        return

    trade_id = trade[0]

    start_time = time.time()
    cursor.execute("""
        INSERT INTO "TradeLogs" (trade_id, time_taken, fee, comment)
        VALUES (%s, %s, %s, %s)
    """, (trade_id, random.randint(1, 5), random.uniform(0.1, 1.0), "Test log"))
    print(f"Query execution time for inserting trade log: {time.time() - start_time} seconds")

    conn.commit()
    cursor.close()
    conn.close()
    update.message.reply_text("Trade log inserted!")

# /convert command
def convert(update, context):
    if len(context.args) != 1:
        update.message.reply_text("Usage: /convert <amount_in_usd>")
        return

    try:
        amount_usd = float(context.args[0])
        zar_amount = usd_to_zar(amount_usd)
        if zar_amount:
            update.message.reply_text(f"${amount_usd} = R{zar_amount}")
        else:
            update.message.reply_text("Couldn't fetch the exchange rate.")
    except ValueError:
        update.message.reply_text("Please send a valid number.")

# Dispatcher handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("trade", trade))
dispatcher.add_handler(CommandHandler("log_trade", log_trade))
dispatcher.add_handler(CommandHandler("convert", convert))

# Webhook handler
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
        return "ok", 200
    except Exception as e:
        print(f"Error processing update: {e}")
        return "error", 500

# Health check
@app.route("/")
def index():
    return "Bot is running."

# Set the webhook
def set_webhook():
    webhook_url = f"{RENDER_URL}/{TOKEN}"
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
    response = requests.get(url)
    print(f"Webhook set response: {response.status_code}")
    print(response.json())

set_webhook()

# IMPORTANT: use port 8080 for Fly.io
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
