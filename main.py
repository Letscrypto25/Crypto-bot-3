import logging
import os
import json
import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

import requests
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.webhook import get_new_configured_app
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from dotenv import load_dotenv
import pyrebase

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Firebase config
firebase_config = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID")
}
firebase = pyrebase.initialize_app(firebase_config)
db = firebase.database()

# --- AES ENCRYPTION HELPERS ---
SECRET_KEY = os.getenv("ENCRYPTION_KEY").encode()  # 16, 24, or 32 bytes

def encrypt_data(data: str):
    cipher = AES.new(SECRET_KEY, AES.MODE_EAX)
    nonce = cipher.nonce
    ciphertext, tag = cipher.encrypt_and_digest(data.encode())
    return base64.b64encode(nonce + ciphertext).decode()

def decrypt_data(enc_data: str):
    raw = base64.b64decode(enc_data)
    nonce = raw[:16]
    ciphertext = raw[16:]
    cipher = AES.new(SECRET_KEY, AES.MODE_EAX, nonce=nonce)
    return cipher.decrypt(ciphertext).decode()

# --- TELEGRAM HANDLERS ---

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    await message.answer("Welcome to the Crypto Trading Bot! Use /setkeys to set your API keys.")

@dp.message_handler(commands=['setkeys'])
async def set_keys(message: types.Message):
    args = message.text.strip().split()
    if len(args) != 4:
        await message.reply("Usage: /setkeys [luno|binance] [API_KEY] [API_SECRET]")
        return

    exchange, api_key, api_secret = args[1].lower(), args[2], args[3]
    if exchange not in ["luno", "binance"]:
        await message.reply("Exchange must be 'luno' or 'binance'.")
        return

    user_id = str(message.from_user.id)
    db.child("users").child(user_id).child(exchange).set({
        "api_key": encrypt_data(api_key),
        "api_secret": encrypt_data(api_secret)
    })
    await message.reply(f"{exchange.capitalize()} keys saved with encryption!")

@dp.message_handler(commands=['balance'])
async def check_balance(message: types.Message):
    user_id = str(message.from_user.id)
    exchange = "luno"

    try:
        keys = db.child("users").child(user_id).child(exchange).get().val()
        if not keys:
            await message.reply("No Luno keys found. Use /setkeys to add them.")
            return

        key = decrypt_data(keys["api_key"])
        secret = decrypt_data(keys["api_secret"])

        # Luno balance request
        response = requests.get(
            "https://api.luno.com/api/1/balance",
            auth=(key, secret)
        )

        if response.status_code != 200:
            await message.reply(f"Luno API error: {response.text}")
            return

        balances = response.json().get("balance", [])
        reply = "Luno Balances:\n" + "\n".join([f"{b['asset']}: {b['balance']}" for b in balances])
        await message.reply(reply)

    except Exception as e:
        await message.reply(f"Error fetching balance: {e}")

# --- FASTAPI SERVER ---

app = FastAPI()

@app.post(WEBHOOK_PATH)
async def webhook_handler(request: Request):
    update = types.Update(**await request.json())
    await dp.process_update(update)

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook set to {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    print("Webhook deleted")
