import os
import base64
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# === Setup ===
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
cred = credentials.Certificate("firebase_credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)

# === Key Functions ===
def derive_key(telegram_id: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(telegram_id.encode()))

def encrypt_api_key(api_key: str, telegram_id: str):
    salt = os.urandom(16)
    key = derive_key(telegram_id, salt)
    f = Fernet(key)
    encrypted = f.encrypt(api_key.encode())
    return encrypted.decode(), base64.b64encode(salt).decode()

def decrypt_api_key(encrypted: str, salt: str, telegram_id: str):
    salt_bytes = base64.b64decode(salt)
    key = derive_key(telegram_id, salt_bytes)
    f = Fernet(key)
    return f.decrypt(encrypted.encode()).decode()

# === Fee Logic ===
def apply_profit_deductions(profit: float, tournament: bool):
    if profit <= 0:
        return profit, 0.0

    if tournament:
        app_fee = profit * 0.0025
        tournament_fee = profit * 0.01
        return profit - app_fee - tournament_fee, app_fee + tournament_fee
    else:
        app_fee = profit * 0.005
        return profit - app_fee, app_fee

# === Bot Commands ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send /api followed by your Binance API key")

async def save_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /api YOUR_API_KEY")
        return
    api_key = args[0]

    encrypted, salt = encrypt_api_key(api_key, telegram_id)
    db.collection("users").document(telegram_id).set({
        "telegram_id": telegram_id,
        "encrypted_api_key": encrypted,
        "salt": salt,
        "tournament": False,
        "balance": 0,
        "total_fees": 0
    }, merge=True)

    await update.message.reply_text("API key saved securely!")

async def join_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    db.collection("users").document(telegram_id).update({"tournament": True})
    await update.message.reply_text("You're now in the tournament!")

# === Simulate a trade ===
async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    doc = db.collection("users").document(telegram_id).get()
    if not doc.exists:
        await update.message.reply_text("No user found.")
        return

    user = doc.to_dict()
    # Simulate trade with random profit
    profit = 100  # Simulated R100 profit
    tournament = user.get("tournament", False)
    net_profit, fee = apply_profit_deductions(profit, tournament)

    db.collection("users").document(telegram_id).update({
        "balance": firestore.Increment(net_profit),
        "total_fees": firestore.Increment(fee)
    })

    await update.message.reply_text(
        f"Trade completed!\nProfit: R{profit:.2f}\nFees: R{fee:.2f}\nNet: R{net_profit:.2f}"
    )

# === Telegram App ===
bot_app = Application.builder().token(TOKEN).build()
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("api", save_api))
bot_app.add_handler(CommandHandler("join", join_tournament))
bot_app.add_handler(CommandHandler("trade", trade))

# === Flask server for Fly.io ===
@app.route("/" + TOKEN, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "Bot running."

if __name__ == "__main__":
    bot_app.run_polling()
