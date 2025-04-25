import os
import psycopg2
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler
import requests

# --- Environment variables ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # Optional for admin-only commands

bot = Bot(token=TOKEN)
app = Flask(__name__)

# --- Database Connection ---
def get_db_connection():
    conn = psycopg2.connect(
        host=SUPABASE_URL.split("/")[2],  # Extract host from URL
        dbname="postgres",
        user="postgres",
        password=SUPABASE_KEY,
        port=5432
    )
    return conn

# --- Telegram Dispatcher ---
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)

# --- Commands ---
def start(update, context):
    telegram_id = update.effective_user.id
    username = update.effective_user.username or "unknown"

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
    existing_user = cursor.fetchone()

    if existing_user:
        update.message.reply_text("Welcome back! You're already registered.")
    else:
        cursor.execute(
            "INSERT INTO users (telegram_id, username, joined_at, balance, profit) VALUES (%s, %s, NOW(), %s, %s)",
            (telegram_id, username, 0.0, 0.0)
        )
        conn.commit()
        update.message.reply_text("Welcome! You have been registered successfully.")

    cursor.close()
    conn.close()

def users(update, context):
    # Only allow admin to use this command
    if str(update.effective_chat.id) != ADMIN_CHAT_ID:
        update.message.reply_text("Unauthorized.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]

    update.message.reply_text(f"Total registered users: {count}")

    cursor.close()
    conn.close
