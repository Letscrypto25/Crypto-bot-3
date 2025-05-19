# tasks.py
import os
from celery import Celery
from telegram import Update
from telegram.ext import Application

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

@celery_app.task(name="tasks.process_update_task")
def process_update_task(update_json):
    update = Update.de_json(update_json, telegram_app.bot)
    telegram_app.process_update(update)
