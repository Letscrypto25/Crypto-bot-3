import sys
import multiprocessing
from celery.bin import worker, beat
from celery_app import celery_app

def run_worker():
    worker.worker(app=celery_app).run(loglevel="info")

def run_beat():
    beat.beat(app=celery_app).run(loglevel="info")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "worker"
    if mode == "worker":
        run_worker()
    elif mode == "beat":
        run_beat()
    elif mode == "both":
        multiprocessing.Process(target=run_worker).start()
        multiprocessing.Process(target=run_beat).start()
