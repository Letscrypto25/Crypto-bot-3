import time
from auto_bot import auto_bot_logic

if __name__ == "__main__":
    while True:
        print("[AUTO] Running arbitrage auto logic...")
        auto_trade_logic()
        time.sleep(60)
