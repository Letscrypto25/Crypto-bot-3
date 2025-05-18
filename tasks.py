from celery import Celery
from telegram import Update
from telegram_app import telegram_app  # import the bot object properly

celery = Celery(
    "tasks",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0")
)

@celery.task(name="tasks.process_update_task")
def process_update_task(update_json):
    update = Update.de_json(update_json, telegram_app.bot)
    telegram_app.process_update(update)
