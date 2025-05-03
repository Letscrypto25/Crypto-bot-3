from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import os
import asyncio
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import json

# --- Firebase Init ---
creds_dict = json.loads(os.environ["FIREBASE_CREDENTIALS"])
cred = credentials.Certificate(creds_dict)
firebase_admin.initialize_app(cred)
db = firestore.client()

# --- Telegram Bot ---
TOKEN = os.environ.get("BOT_TOKEN")
app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)  # Convert user_id to string
    username = update.effective_user.username or "unknown"
    user_ref = db.collection("users").document(user_id)  # Use user_id (as string) as document ID
    
    if not user_ref.get().exists:
        user_ref.set({
            "user_id": user_id,  # Store user_id as a string
            "username": username,
            "balance": 500,
            "joined": datetime.datetime.utcnow().isoformat()
        })
        await update.message.reply_text(f"Welcome, {username}! R500 balance has been added to your account.")
    else:
        await update.message.reply_text("Welcome back!")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_ref = db.collection("users").document(user_id).get()

    if user_ref.exists:
        balance = user_ref.to_dict().get("balance", 0)
        await update.message.reply_text(f"Your current balance is R{balance}")
    else:
        await update.message.reply_text("Please use /start first to initialize your account.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Available commands:\n/start\n/help\n/balance")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sorry, I didn't understand that command.")

# --- Register Handlers ---
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("balance", balance))
application.add_handler(MessageHandler(filters.COMMAND, unknown))

# --- Webhook route ---
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "ok", 200

@app.route("/", methods=["GET"])
def home():
    return "Telegram bot is running via webhook!", 200

# --- Run Server ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
