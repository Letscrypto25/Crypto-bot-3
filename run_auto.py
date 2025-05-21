import time
from auto_bot import run_auto_bot

if __name__ == "__main__":
    while True:
        print("[AUTO] Running auto bot...")
        run_auto_bot()
        time.sleep(60)
