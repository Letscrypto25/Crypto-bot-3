from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
from telegram.ext import ConversationHandler
import os
import requests
from supabase import create_client, Client
from flask import Flask

# Initialize bot and app
TOKEN = "7874445351:AAF0pI0tuwPvTQT2wS-u8nrK96ic9opTdfY"  # Your bot token
RENDER_URL = "https://crypto-bot-3-10.onrender.com"  # Your Render URL

bot = Bot(token=TOKEN)
app = Flask(__name__)

# Supabase setup
url = "https://pqdqcthnimeurvdqpdlu.supabase.co"  # Your Supabase URL
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBxZHFjdGhuaW1ldXJ2ZHFwZGx1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDU1NTk1MjcsImV4cCI6MjA2MTEzNTUyN30.Rjub8T1OPZM0lgOlN57ybMvUpmyj2z8i6rokakx1sWo"  # Your Supabase API Key
supabase: Client = create_client(url, key)

# States for conversation
ID_COLLECTION = range(1)

# Start command to welcome user and initiate ID collection
def start(update, context):
    update.message.reply_text("Welcome! Please provide your ID to get started.")
    return ID_COLLECTION

# Handle the collected ID and store it in the database
def collect_id(update, context):
    user_id = update.message.text
    username = update.message.from_user.username
    telegram_id = update.message.from_user.id

    # Insert data into Supabase
    response = supabase.table("users").insert({
        "telegram_id": str(telegram_id),
        "username": username,
        "user_id": user_id,  # Assuming user ID is what they enter
        "joined_at": "now()"
    }).execute()

    update.message.reply_text(f"Thanks for providing your ID! Your ID: {user_id} has been saved.")
    return ConversationHandler.END  # End the conversation

# If the bot receives a non-ID response, it will ask again
def cancel(update, context):
    update.message.reply_text("You can always type /start to begin again.")
    return ConversationHandler.END

# Conversation handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ID_COLLECTION: [MessageHandler(Filters.text & ~Filters.command, collect_id)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Dispatcher to add the conversation handler
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)
dispatcher.add_handler(conv_handler)

# Webhook route
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# Health check
@app.route("/")
def index():
    return "Bot is running via webhook."

# Webhook setup function
def set_webhook():
    webhook_url = f"{RENDER_URL}/{TOKEN}"
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
    response = requests.get(url)
    print(response.status_code)
    print(response.json())

# Set webhook when app starts
set_webhook()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
