from flask import Flask, request
import os
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")
    
    # Simple command response
    if text.lower() == "/start":
        reply = "Welcome to the bot! You're now connected to Firebase."
    else:
        reply = f"You said: {text}"

    # Example Firebase write
    db.collection("messages").add({"chat_id": chat_id, "text": text})

    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": reply
    })
    return {"ok": True}

@app.route("/", methods=["GET"])
def root():
    return "Bot is running"

if __name__ == "__main__":
    app.run(port=8080)