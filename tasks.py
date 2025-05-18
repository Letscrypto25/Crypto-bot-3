import os
from celery import Celery
from telegram import Update
from telegram_app import telegram_app  # import the bot object properly


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
  # queues it async
# Setup
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Celery app
celery_app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Telegram Application
telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Add handlers here if needed:
# from your_handlers import start
# telegram_app.add_handler(CommandHandler("start", start))

@celery_app.task(name="tasks.process_update_task")
def process_update_task(update_json):
    update = Update.de_json(update_json, telegram_app.bot)
    telegram_app.process_update(update)
