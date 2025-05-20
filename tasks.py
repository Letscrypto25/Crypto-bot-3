from celery_app import celery_app

@celery_app.task(name="tasks.run_auto_bot_task")
def run_auto_bot_task(payload=None):
    print("Running auto bot task...")
    # Your trading logic here
    return {"status": "success"}
