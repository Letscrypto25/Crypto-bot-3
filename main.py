import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import firebase_admin
from firebase_admin import credentials, db
from cryptography.fernet import Fernet
import httpx
import hmac
import hashlib
import time

# Load env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
DB_URL = os.getenv("FIREBASE_DB_URL")
FERNET_KEY = os.getenv("FERNET_KEY")
fernet = Fernet(FERNET_KEY)

# Firebase
cred = credentials.Certificate("firebase.json")
firebase_admin.initialize_app(cred, {"databaseURL": DB_URL})

# Telegram + FastAPI
app = FastAPI()
bot = Bot(token=TOKEN)
application = ApplicationBuilder().token(TOKEN).build()

@app.post(f"/webhook/{TOKEN}")
async def telegram_webhook(req: Request):
    data = await req.json()
    await application.process_update(Update.de_json(data, bot))
    return {"status": "ok"}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Crypto Trading Bot! Use /setkeys <luno|binance> <key> <secret>")

# /setkeys
async def setkeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args
    if len(args) != 3:
        await update.message.reply_text("Usage: /setkeys <luno|binance> <api_key> <api_secret>")
        return

    exchange, api_key, api_secret = args
    if exchange.lower() not in ["luno", "binance"]:
        await update.message.reply_text("Exchange must be 'luno' or 'binance'")
        return

    encrypted_key = fernet.encrypt(api_key.encode()).decode()
    encrypted_secret = fernet.encrypt(api_secret.encode()).decode()
    db.reference(f"users/{user_id}/{exchange.lower()}").set({
        "api_key": encrypted_key,
        "api_secret": encrypted_secret
    })

    await update.message.reply_text(f"{exchange.capitalize()} keys saved.")

# /balance <luno|binance>
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args
    if len(args) != 1 or args[0].lower() not in ["luno", "binance"]:
        await update.message.reply_text("Usage: /balance <luno|binance>")
        return

    exchange = args[0].lower()
    ref = db.reference(f"users/{user_id}/{exchange}").get()
    if not ref:
        await update.message.reply_text(f"Please set your {exchange.capitalize()} keys using /setkeys")
        return

    try:
        api_key = fernet.decrypt(ref["api_key"].encode()).decode()
        api_secret = fernet.decrypt(ref["api_secret"].encode()).decode()
    except Exception:
        await update.message.reply_text("Decryption failed.")
        return

    if exchange == "luno":
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    'https://api.luno.com/api/1/balance',
                    auth=(api_key, api_secret)
                )
            data = r.json()
            if 'balance' in data:
                balances = "\n".join([f"{b['asset']}: {b['balance']}" for b in data['balance']])
                await update.message.reply_text(f"Luno Balance:\n{balances}")
            else:
                await update.message.reply_text(f"Luno error: {data}")
        except Exception as e:
            await update.message.reply_text("Error contacting Luno.")
    elif exchange == "binance":
        try:
            timestamp = int(time.time() * 1000)
            query = f"timestamp={timestamp}"
            signature = hmac.new(api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
            url = f"https://api.binance.com/api/v3/account?{query}&signature={signature}"

            headers = {"X-MBX-APIKEY": api_key}
            async with httpx.AsyncClient() as client:
                r = await client.get(url, headers=headers)
            data = r.json()
            if 'balances' in data:
                non_zero = [b for b in data['balances'] if float(b['free']) > 0]
                balances = "\n".join([f"{b['asset']}: {b['free']}" for b in non_zero])
                await update.message.reply_text(f"Binance Balance:\n{balances if balances else 'Empty'}")
            else:
                await update.message.reply_text(f"Binance error: {data}")
        except Exception as e:
            await update.message.reply_text("Error contacting Binance.")

# Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("setkeys", setkeys))
application.add_handler(CommandHandler("balance", balance))

# Start
if __name__ == "__main__":
    import uvicorn
    print("Running bot...")
    uvicorn.run(app, host="0.0.0.0", port=8080)
