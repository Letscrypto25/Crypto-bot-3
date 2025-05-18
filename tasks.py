from celery import Celery
from telegram import Update
from telegram.ext import Application
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

celery_app = Celery("tasks", broker=os.getenv("REDIS_URL"))

@celery_app.task
def process_update_task(update_json):
    update = Update.de_json(update_json, telegram_app.bot)
    telegram_app.process_update(update)  # sync version