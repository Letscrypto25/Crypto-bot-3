import os
from celery import Celery
from telegram import Update
from telegram.ext import Application
import firebase_admin
from firebase_admin import credentials, db

# Load env variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")

# Initialize Celery
celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

# Initialize Telegram Application
telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Initialize Firebase Admin SDK once
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_DATABASE_URL
    })

@celery_app.task(name="tasks.send_telegram_message")
def send_telegram_message(text, chat_id=None):
    """Send message to Telegram user or channel."""
    chat = chat_id or os.getenv("TELEGRAM_CHAT_ID")
    if not chat:
        print("No chat_id provided or set in env TELEGRAM_CHAT_ID")
        return

    async def send():
        await telegram_app.bot.send_message(chat_id=chat, text=text)

    import asyncio
    asyncio.run(send())

@celery_app.task(name="tasks.process_update_task")
def process_update_task(update_json):
    update = Update.de_json(update_json, telegram_app.bot)
    telegram_app.process_update(update)

@celery_app.task(name="tasks.update_leaderboard")
def update_leaderboard():
    ref = db.reference('user_stats')
    all_stats = ref.get()

    if not all_stats:
        print("No user stats found for leaderboard")
        return

    leaderboard = sorted(all_stats.items(), key=lambda x: x[1].get('profit', 0), reverse=True)
    top10 = leaderboard[:10]

    leaderboard_ref = db.reference('leaderboard')
    leaderboard_ref.set({user_id: data for user_id, data in top10})

    top_user_id, top_data = top10[0]
    message = f"Leaderboard Updated! Top trader: {top_user_id} with profit {top_data.get('profit', 0)}"
    send_telegram_message.delay(message)

@celery_app.task(name="tasks.start_trading_bot")
def start_trading_bot(bot_id):
    db.reference(f'bots/{bot_id}/status').set('running')
    print(f"Trading bot {bot_id} started")
    send_telegram_message.delay(f"Trading bot {bot_id} has started.")

@celery_app.task(name="tasks.stop_trading_bot")
def stop_trading_bot(bot_id):
    db.reference(f'bots/{bot_id}/status').set('stopped')
    print(f"Trading bot {bot_id} stopped")
    send_telegram_message.delay(f"Trading bot {bot_id} has stopped.")
