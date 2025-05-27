# strategy_loop.py

import asyncio
from database import get_all_users, get_user, get_autobot_status
from auto_bot import run_auto_bot
from strategies.arbitrage import run_arbitrage
from strategies.momentum_trading import run_momentum
from strategies.mean_reverse import run_mean_reversion
from strategies.trend_follow import run_trend_follow
from strategies.range_trader import run_range
from strategies.dip_buyer import run_dip_buyer
from utils import log_event

# Arbitrage runs faster (every 20s), rest are slower
ARBITRAGE_INTERVAL = 20
BINANCE_INTERVAL = 60
LUNO_INTERVAL = 300

async def run_user_strategies(user_id):
    while True:
        user = get_user(user_id)
        if not user or not user.get("active") or not get_autobot_status(user_id):
            await asyncio.sleep(10)
            continue

        exchange = user.get("exchange")
        try:
            # Run arbitrage (between both if available)
            await run_arbitrage(user_id)

            # Run user's configured strategy based on platform
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
    await run_range(user_id)

async def strategy_loop():
    await asyncio.sleep(10)  # allow startup tasks
    users = get_all_users()
    for user_id in users:
        asyncio.create_task(run_user_strategies(user_id))
