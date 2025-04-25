import os
import psycopg2
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler
import requests

# Get tokens and credentials
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # Add this in Render env vars

bot = Bot(token=TOKEN)
app = Flask(__name__)

# Set up PostgreSQL (Supabase) connection
def get_db_connection():
    conn = psycopg2.connect(
        host=SUPABASE_URL.split("/")[2],
        dbname="postgres",
        user="postgres",
        password=SUPABASE_KEY,
        port=5432
    )
    return conn

# Dispatcher
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)

# Telegram /start command
def start(update, context):
    update.message.reply_text("Welcome! Webhook is live and working.")

dispatcher.add_handler(CommandHandler("start", start))

# Webhook endpoint
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# Health check
@app.route("/")
def index():
    return "Bot is running via webhook."

# Set webhook on app start
def set_webhook():
    webhook_url = f"{os.getenv('RENDER_EXTERNAL_URL')}/{TOKEN}"  # Fixed to use Render's real URL
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
    response = requests.get(url)
    print(response.status_code)
    print(response.json())

set_webhook()

# Insert new Telegram user into database
def insert_user_data(telegram_id, username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (telegram_id, username, joined_at, balance, profit) VALUES (%s, %s, now(), 0, 0)",
        (telegram_id, username)
    )
    conn.commit()
    cursor.close()
    conn.close()

# ---------------------------- NEW PARTS BELOW ----------------------------

# App: Register new Crypto User
@app.route("/register_app", methods=["POST"])
def register_app_user():
    data = request.json
    telegram_id = data.get("telegram_id")
    username = data.get("username")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO \"Crypto Users\" (telegram_id, username, joined_at, balance, profit) VALUES (%s, %s, now(), 0, 0)",
        (telegram_id, username)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "App user registered"}, 200

# App: Record a trade for Crypto User
@app.route("/trade", methods=["POST"])
def record_trade():
    data = request.json
    telegram_id = data.get("telegram_id")
    profit = data.get("profit")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE \"Crypto Users\" SET profit = profit + %s WHERE telegram_id = %s",
        (profit, telegram_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

    # Notify on Telegram
    bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"User {telegram_id} made a profit of R{profit}!")

    return {"status": "Trade recorded"}, 200

# --------------------------------------------------------------------------

# Run Flask app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
