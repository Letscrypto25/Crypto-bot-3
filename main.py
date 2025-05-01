
import os
from flask import Flask, request
import telegram

app = Flask(__name__)
bot = telegram.Bot(token=os.environ['TELEGRAM_TOKEN'])

@app.route(f"/{os.environ['TELEGRAM_TOKEN']}", methods=["POST"])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    chat_id = update.message.chat.id
    message = update.message.text
    bot.send_message(chat_id=chat_id, text="Echo: " + message)
    return "ok"

@app.route("/")
def index():
    return "Bot is running."

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 8080)), host="0.0.0.0")
