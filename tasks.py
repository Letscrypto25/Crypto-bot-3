from celery import Celery
from telegram import Update
from telegram.ext import Application
import os

# Setup
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Celery app
celery_app = Celery("tasks", broker=REDIS_URL)

# Telegram Application
telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Add handlers here if needed:
# from your_handlers import start
# telegram_app.add_handler(CommandHandler("start", start))

@celery_app.task
def process_update_task(update_json):
    update = Update.de_json(update_json, telegram_app.bot)
    telegram_app.update_queue.put(update)  # queues it async
