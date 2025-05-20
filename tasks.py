import os import asyncio from celery import Celery from telegram import Update from telegram.ext import Application import firebase_admin from firebase_admin import credentials, db from binance.client import Client as BinanceClient from luno_python.client import Client as LunoClient

Load environment variables

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0") FIREBASE_CREDENTIALS_ENCODED = os.getenv("FIREBASE_CREDENTIALS_ENCODED") FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")

Initialize Celery

celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

Initialize Telegram bot

telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

Firebase init

if not firebase_admin._apps: cred = credentials.Certificate(FIREBASE_CREDENTIALS_ENCODED) firebase_admin.initialize_app(cred, { 'databaseURL': FIREBASE_DATABASE_URL })

@celery_app.task(name="tasks.send_telegram_message") def send_telegram_message(text, chat_id=None): chat = chat_id or os.getenv("TELEGRAM_CHAT_ID") if not chat: print("No chat_id provided or set in env TELEGRAM_CHAT_ID") return

async def send():
    await telegram_app.bot.send_message(chat_id=chat, text=text)

asyncio.run(send())

@celery_app.task(name="tasks.process_update_task") def process_update_task(update_json): update = Update.de_json(update_json, telegram_app.bot) telegram_app.process_update(update)

@celery_app.task(name="tasks.update_leaderboard") def update_leaderboard(): ref = db.reference('user_stats') all_stats = ref.get() if not all_stats: print("No user stats found for leaderboard") return

leaderboard = sorted(all_stats.items(), key=lambda x: x[1].get('profit', 0), reverse=True)
top10 = leaderboard[:10]
leaderboard_ref = db.reference('leaderboard')
leaderboard_ref.set({user_id: data for user_id, data in top10})

top_user_id, top_data = top10[0]
message = f"Leaderboard Updated! Top trader: {top_user_id} with profit {top_data.get('profit', 0)}"
send_telegram_message.delay(message)

@celery_app.task(name="tasks.start_trading_bot") def start_trading_bot(bot_id): db.reference(f'bots/{bot_id}/status').set('running') print(f"Trading bot {bot_id} started") send_telegram_message.delay(f"Trading bot {bot_id} has started.")

@celery_app.task(name="tasks.stop_trading_bot") def stop_trading_bot(bot_id): db.reference(f'bots/{bot_id}/status').set('stopped') print(f"Trading bot {bot_id} stopped") send_telegram_message.delay(f"Trading bot {bot_id} has stopped.")

@celery_app.task(name="tasks.run_auto_bot_task") def run_auto_bot_task(): bots_ref = db.reference('bots') all_bots = bots_ref.get() if not all_bots: print("No bots found in Firebase.") return

for bot_id, bot_data in all_bots.items():
    if bot_data.get('status') != 'running':
        continue

    exchange = bot_data.get('exchange')
    api_key = bot_data.get('api_key')
    api_secret = bot_data.get('api_secret')
    symbol = bot_data.get('symbol', 'BTCUSDT')
    amount = bot_data.get('amount', 10)
    user_id = bot_data.get('user_id')

    try:
        if exchange == 'binance':
            client = BinanceClient(api_key, api_secret)
            price = float(client.get_symbol_ticker(symbol=symbol)['price'])
            order = client.order_market_buy(symbol=symbol, quantity=amount / price)
            profit = price * (amount / price) - amount
        elif exchange == 'luno':
            client = LunoClient(api_key_id=api_key, api_key_secret=api_secret)
            ticker = client.get_ticker(pair=symbol.lower())
            price = float(ticker['ask'])
            order = client.post_market_order(pair=symbol.lower(), type='BUY', counter_volume=amount)
            profit = price * float(order['counter']) - amount
        else:
            continue

        # Update stats
        if user_id:
            stats_ref = db.reference(f'user_stats/{user_id}')
            current_stats = stats_ref.get() or {}
            current_profit = current_stats.get('profit', 0)
            new_profit = current_profit + profit
            stats_ref.update({'profit': new_profit})

    except Exception as e:
        print(f"Error for bot {bot_id}: {e}")
        send_telegram_message.delay(f"Bot {bot_id} error: {e}")

print("Auto bot task completed.")

