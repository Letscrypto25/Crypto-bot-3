from celery import Celery
import os

CELERY_BROKER = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("tasks", broker=CELERY_BROKER, backend=CELERY_BROKER)
celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "run-every-5-minutes": {
            "task": "tasks.run_auto_bot_task",
            "schedule": 300.0,  # 5 minutes
            "args": [],
        }
    }
)

