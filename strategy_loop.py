import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_all_users, get_user_data, get_autobot_status
from trading_api import get_binance_price, get_luno_price, trade_on_binance, trade_on_luno
from strategies.arbitrage import execute as run_arbitrage_strategy
from strategies.dip_buyer import execute as run_dip_buyer
from strategies.mean_reverse import execute as run_mean_reversion
from strategies.momentum_trading import execute as run_momentum
from strategies.range_trader import execute as run_range_trader
from strategies.trend_follow import execute as run_trend_follow
from utils import log_event

# Strategy intervals
ARBITRAGE_INTERVAL = 20
ARBITRAGE_MIN_PROFIT = 0.5  # percent

async def run_arbitrage(user_id):
    user = get_user(user_id)
    if not user:
        return

    try:
        binance_price = get_binance_price("BTCUSDT")
        luno_price = get_luno_price("XBTZAR")
        zar_usdt = user.get("zar_usdt_rate", 18.5)

        luno_usd_price = luno_price / zar_usdt
        price_diff = binance_price - luno_usd_price
        percent_diff = (price_diff / luno_usd_price) * 100

        if percent_diff >= ARBITRAGE_MIN_PROFIT:
            log_event(user_id, "arbitrage_opportunity",
                      f"Buy on Luno ({luno_usd_price:.2f}) sell on Binance ({binance_price:.2f}) | Profit: {percent_diff:.2f}%")
            luno_result = trade_on_luno(user, "buy", amount=200)
            binance_result = trade_on_binance(user, "sell", amount=None)
            log_event(user_id, "arbitrage_trade", f"Executed Arbitrage: {luno_result} | {binance_result}")

    except Exception as e:
        log_event(user_id, "arbitrage_error", f"Arbitrage failed: {e}", status="error", error=e)

async def run_user_strategies(user_id):
    while True:
        user = get_user(user_id)
        if not user or not user.get("active") or not get_autobot_status(user_id):
            await asyncio.sleep(10)
            continue

        exchange = user.get("exchange")

        try:
            await run_arbitrage(user_id)

            if exchange == "binance":
                await run_binance_strategies(user_id)
            elif exchange == "luno":
                await run_luno_strategies(user_id)
            elif exchange == "both":
                await asyncio.gather(
                    run_binance_strategies(user_id),
                    run_luno_strategies(user_id)
                )

        except Exception as e:
            log_event(user_id, "strategy_error", f"Strategy error: {e}", status="error", error=e)

        await asyncio.sleep(ARBITRAGE_INTERVAL)

async def run_binance_strategies(user_id):
    await asyncio.sleep(5)
    await run_momentum(user_id)
    await run_trend_follow(user_id)
    await run_dip_buyer(user_id)

async def run_luno_strategies(user_id):
    await asyncio.sleep(5)
    await run_mean_reversion(user_id)
    await run_range_trader(user_id)

async def strategy_loop():
    user_tasks = {}

    while True:
        users_data = get_all_users() or {}

        for user_id, user_data in users_data.items():
            autobot_status = get_autobot_status(user_id)
            active = user_data.get("active", False)

            if active and autobot_status:
                if user_id not in user_tasks or user_tasks[user_id].done():
                    task = asyncio.create_task(run_user_strategies(user_id))
                    user_tasks[user_id] = task
                    log_event(user_id, "autobot_start", "Autobot started for user.")
            else:
                task = user_tasks.get(user_id)
                if task and not task.done():
                    task.cancel()
                    log_event(user_id, "autobot_stop", "Autobot stopped for user.")

        await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(strategy_loop())
    except KeyboardInterrupt:
        print("Shutting down gracefully.")
