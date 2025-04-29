# -*- coding: utf-8 -*-
import os
import psycopg2
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler
import requests
import random

# Environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize bot and Flask app
bot = Bot(token=TOKEN)
app = Flask(__name__)

# Fixed DB connection for Supabase with SSL
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host="db.pqdqcthnimeurvdqpdlu.supabase.co",
            dbname="postgres",
            user="postgres",
            password=SUPABASE_KEY,
            port=5432,
            sslmode='require',
            connect_timeout=5
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        return None

# Dispatcher for Telegram bot
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)

# Convert USD to ZAR
def usd_to_zar(amount_usd):
    try:
        response = requests.get('https://api.exchangerate.host/latest?base=USD&symbols=ZAR')
        data = response.json()
        rate = data['rates']['ZAR']
        return round(amount_usd * rate, 2)
    except Exception as e:
        print(f"Error fetching exchange rate: {str(e)}")
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
    cursor.execute('SELECT id FROM "Users" ORDER BY RANDOM() LIMIT 1;')
    user = cursor.fetchone()

    if not user:
        update.message.reply_text("No users found. Please /start first.")
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
        update.message.reply_text("Failed to connect to the database.")
        return

    cursor = conn.cursor()
    cursor.execute('SELECT id FROM "Trades" ORDER BY RANDOM() LIMIT 1;')
    trade = cursor.fetchone()

    if not trade:
        update.message.reply_text("No trades to log. Insert a trade first.")
        return

    trade_id = trade[0]
    cursor.execute("""
        INSERT INTO "TradeLogs" (trade_id, time_taken, fee, comment)
        VALUES (%s, %s, %s, %s)
    """, (trade_id, random.randint(1, 5), random.uniform(0.1, 1.0), "Test log"))

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

# Add handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("trade", trade))
dispatcher.add_handler(CommandHandler("log_trade", log_trade))
dispatcher.add_handler(CommandHandler("convert", convert))

# Webhook route
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
        return "ok", 200
    except Exception as e:
        print(f"Error processing update: {str(e)}")
        return "error", 500

# Health check
@app.route("/")
def index():
    return "Bot is running on crypto-bot-3.fly.dev."

# Run app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host="0.0.0.0", port=port)
