import os
from flask import Flask, request
import telegram

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')  # Set this to your Fly.io app URL + /token

bot = telegram.Bot(token=TELEGRAM_TOKEN)

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    if update.message:  # Ensure message exists
        chat_id = update.message.chat.id
        message = update.message.text
        bot.send_message(chat_id=chat_id, text="Echo: " + message)
    return "ok"

@app.route("/")
def index():
    return "Bot is running."

@app.before_first_request
def set_webhook():
    if WEBHOOK_URL:
        full_webhook_url = f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
        bot.set_webhook(url=full_webhook_url)
        print(f"Webhook set to: {full_webhook_url}")
    else:
        print("WEBHOOK_URL not set.")

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 8080)), host="0.0.0.0")
