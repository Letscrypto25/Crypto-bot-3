import time
from trading_api import trading_api_logic

if __name__ == "__main__":
    while True:
        print("[AUTO] Running arbitrage auto logic...")
        auto_trade_logic()
        time.sleep(60)
