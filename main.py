import os
import base64
import logging
import python-telegram-bot
from dotenv import load_dotenv
from telegram import Update

import firebase_admin
from firebase_admin import credentials, firestore
from telegram.ext import Application, CommandHandler, MessageHandler, filters
# === Load environment variables ===
load_dotenv()

# === Logging setup ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# === Firebase Initialization (from base64 JSON) ===
try:
    if not firebase_admin._apps:
        firebase_json_b64 = os.getenv("FIREBASE_CREDENTIALS_JSON")
        if not firebase_json_b64:
            raise ValueError("FIREBASE_CREDENTIALS_JSON env var not set or empty")

        # Decode base64 to UTF-8 JSON string
        firebase_json_str = base64.b64decode(firebase_json_b64).decode("utf-8")

        # Write decoded credentials to temp file
        firebase_cred_path = "/tmp/firebase_credentials.json"
        with open(firebase_cred_path, "w", encoding="utf-8") as f:
            f.write(firebase_json_str)

        # Initialize Firebase with credentials
        cred = credentials.Certificate(firebase_cred_path)
        firebase_admin.initialize_app(cred)

        # Initialize Firestore client
        db = firestore.client()
        logger.info("Firebase initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {e}")
    raise

# === Telegram Bot Setup ===
telegram_token = os.getenv("BOT_TOKEN")
if not telegram_token:
    raise ValueError("BOT_TOKEN environment variable not set")

telegram_app = Application.builder().token(telegram_token).build()
logger.info("Telegram bot initialized successfully")

def get_user_data(user_id):
    return db.reference(f"users/{user_id}").get() or {}

def update_user_data(user_id, data):
    ref = db.reference(f"users/{user_id}")
    ref.update(data)

def save_trade(user_id, trade_data):
    ref = db.reference(f"trades/{user_id}")
    ref.push(trade_data)

# === Telegram Commands ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Crypto Bot! Use /help for available commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
Commands:
/start - Welcome message
/help - List of commands
/register <exchange> <api_key> <api_secret> - Register your API keys
/balance - Show your current balance
/trade <BUY/SELL> <symbol> <amount> - Execute a trade
""")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args

    if len(args) != 3:
        await update.message.reply_text("Usage: /register <binance/luno> <api_key> <api_secret>")
        return

    exchange, api_key, api_secret = args[0].lower(), args[1], args[2]
    if exchange not in ["binance", "luno"]:
        await update.message.reply_text("Exchange must be 'binance' or 'luno'")
        return

    update_user_data(user_id, {
        "exchange": exchange,
        "api_key": api_key,
        "api_secret": api_secret
    })

    await update.message.reply_text(f"Registered {exchange} API keys.")

# === Exchange Client Utilities ===

def get_binance_client(user_data):
    return BinanceClient(user_data['api_key'], user_data['api_secret'])

def get_luno_auth(user_data):
    return HTTPBasicAuth(user_data['api_key'], user_data['api_secret'])

# === Balance Command ===

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if 'exchange' not in user_data:
        await update.message.reply_text("You're not registered. Use /register first.")
        return

    try:
        if user_data['exchange'] == 'binance':
            client = get_binance_client(user_data)
            acc = client.get_account()
            text = "\\n".join([f"{b['asset']}: {b['free']}" for b in acc['balances'] if float(b['free']) > 0])
        elif user_data['exchange'] == 'luno':
            resp = requests.get("https://api.luno.com/api/1/balance", auth=get_luno_auth(user_data)).json()
            text = "\\n".join([f"{bal['asset']}: {bal['balance']}" for bal in resp['balance']])
        else:
            text = "Exchange not recognized."

        await update.message.reply_text(text)
    except Exception as e:
        logger.exception("Balance fetch error")
        await update.message.reply_text(f"Error: {e}")
        
# === main.py (Lines 501–1000) ===

# === Trade Execution Command ===

async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if 'exchange' not in user_data:
        await update.message.reply_text("You're not registered. Use /register first.")
        return

    try:
        action, symbol, amount = context.args[0].upper(), context.args[1].upper(), float(context.args[2])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /trade <BUY/SELL> <SYMBOL> <AMOUNT>")
        return

    try:
        price = None
        if user_data['exchange'] == 'binance':
            client = get_binance_client(user_data)
            if action == "BUY":
                order = client.order_market_buy(symbol=symbol, quantity=amount)
            elif action == "SELL":
                order = client.order_market_sell(symbol=symbol, quantity=amount)
            price = order['fills'][0]['price']
        elif user_data['exchange'] == 'luno':
            market = symbol.lower()
            url = f"https://api.luno.com/api/1/marketorder"
            side = "BUY" if action == "BUY" else "SELL"
            data = {"pair": market, "type": side.lower(), "counter_volume": str(amount)}
            resp = requests.post(url, auth=get_luno_auth(user_data), data=data)
            result = resp.json()
            price = result.get("average_price") or "unknown"
        else:
            await update.message.reply_text("Exchange not recognized.")
            return

        trade_record = {
            "symbol": symbol,
            "amount": amount,
            "side": action,
            "price": price,
            "timestamp": datetime.utcnow().isoformat()
        }
        save_trade(user_id, trade_record)

        await update.message.reply_text(f"{action} {amount} {symbol} at {price} — Executed")
    except Exception as e:
        logger.exception("Trade error")
        await update.message.reply_text(f"Trade failed: {e}")
    
# === main.py (Lines 1001–1500) ===

# === Firebase Leaderboard ===

def update_leaderboard(user_id, profit):
    ref = db.reference("leaderboard")
    current = ref.get() or {}
    previous = current.get(str(user_id), 0)
    current[str(user_id)] = previous + profit
    ref.set(current)

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ref = db.reference("leaderboard")
    data = ref.get() or {}
    top = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
    lines = [f"{i+1}. User {uid}: {profit:.2f}" for i, (uid, profit) in enumerate(top)]
    await update.message.reply_text("Leaderboard:\n" + "\\n".join(lines))

# === Start Bot ===

def main():
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("register", register))
    telegram_app.add_handler(CommandHandler("balance", balance))
    telegram_app.add_handler(CommandHandler("trade", trade))
    telegram_app.add_handler(CommandHandler("leaderboard", leaderboard))
    telegram_app.run_polling()

if __name__ == "__main__":
    main()
    
# === main.py (Lines 1501–2000) ===

import threading
import math

# === Auto Bot State ===
AUTO_BOT_INTERVAL = 300  # in seconds (5 minutes)
AUTO_BOT_ACTIVE = {}

# === Bot Strategy Helpers ===

def get_latest_price(symbol, exchange, user_data):
    if exchange == "binance":
        client = get_binance_client(user_data)
        price = client.get_symbol_ticker(symbol=symbol)['price']
        return float(price)
    elif exchange == "luno":
        market = symbol.lower()
        url = f"https://api.luno.com/api/1/ticker?pair={market}"
        resp = requests.get(url).json()
        return float(resp['last_trade'])
    return None

def calculate_sma(symbol, interval, period, user_data):
    if user_data['exchange'] == "binance":
        client = get_binance_client(user_data)
        klines = client.get_klines(symbol=symbol, interval=interval, limit=period)
        closes = [float(k[4]) for k in klines]
        return sum(closes) / len(closes)
    return None

def calculate_risk_amount(balance, risk_percent, price):
    return round((balance * risk_percent / 100) / price, 6)

# === Auto Bot Core ===

def run_autobot_for_user(user_id, user_data):
    try:
        autobot = user_data.get("auto_bot", {})
        if not autobot.get("enabled", False):
            return

        symbol = autobot["symbol"]
        timeframe = autobot.get("timeframe", "1h")
        strategy = autobot.get("strategy", "sma")
        risk_percent = float(autobot.get("risk_percent", 1))
        tp_pct = float(autobot.get("take_profit", 4.0))
        sl_pct = float(autobot.get("stop_loss", 2.0))

        # Fetch price
        price = get_latest_price(symbol, user_data['exchange'], user_data)
        sma = calculate_sma(symbol, timeframe, 20, user_data)

        if not price or not sma:
            return

        if price > sma:
            # Simulate entry condition (buy when price above SMA)
            logger.info(f"Auto Bot: {symbol} entry triggered for user {user_id} at {price}")

            # Get balance (USDT)
            if user_data['exchange'] == "binance":
                client = get_binance_client(user_data)
                balance_data = client.get_asset_balance("USDT")
                balance = float(balance_data['free'])
            elif user_data['exchange'] == "luno":
                resp = requests.get("https://api.luno.com/api/1/balance", auth=get_luno_auth(user_data)).json()
                usdt_bal = next((b for b in resp['balance'] if b['asset'] == "USDT"), None)
                balance = float(usdt_bal['balance']) if usdt_bal else 0
            else:
                balance = 0

            if balance <= 0:
                logger.warning(f"No balance for user {user_id}")
                return

            qty = calculate_risk_amount(balance, risk_percent, price)

            # Place order
            if user_data['exchange'] == "binance":
                order = client.order_market_buy(symbol=symbol, quantity=qty)
                entry_price = float(order['fills'][0]['price'])
            elif user_data['exchange'] == "luno":
                market = symbol.lower()
                data = {"pair": market, "type": "buy", "counter_volume": str(qty)}
                resp = requests.post("https://api.luno.com/api/1/marketorder", auth=get_luno_auth(user_data), data=data)
                result = resp.json()
                entry_price = float(result.get("average_price", price))
            else:
                return

            # Monitor trade for TP/SL
            monitor_thread = threading.Thread(
                target=monitor_trade,
                args=(user_id, symbol, entry_price, tp_pct, sl_pct, user_data)
            )
            monitor_thread.start()

    except Exception as e:
        logger.exception(f"Auto Bot failed for user {user_id}")

# === Monitor TP/SL ===

def monitor_trade(user_id, symbol, entry_price, tp_pct, sl_pct, user_data):
    tp_price = entry_price * (1 + tp_pct / 100)
    sl_price = entry_price * (1 - sl_pct / 100)
    logger.info(f"Monitoring trade for user {user_id} - TP: {tp_price}, SL: {sl_price}")

    while True:
        time.sleep(30)
        price = get_latest_price(symbol, user_data['exchange'], user_data)
        if not price:
            continue

        if price >= tp_price or price <= sl_price:
            logger.info(f"Exit condition met at {price} for user {user_id}")
            try:
                qty = calculate_risk_amount(price * 1000, 1, price)  # simulate qty to exit
                if user_data['exchange'] == "binance":
                    client = get_binance_client(user_data)
                    client.order_market_sell(symbol=symbol, quantity=qty)
                elif user_data['exchange'] == "luno":
                    market = symbol.lower()
                    data = {"pair": market, "type": "sell", "base_volume": str(qty)}
                    requests.post("https://api.luno.com/api/1/marketorder", auth=get_luno_auth(user_data), data=data)

                profit = (price - entry_price) * qty
                save_trade(user_id, {
                    "symbol": symbol,
                    "amount": qty,
                    "side": "CLOSE",
                    "price": price,
                    "profit": profit,
                    "timestamp": datetime.utcnow().isoformat()
                })
                update_leaderboard(user_id, profit)
                return
            except Exception as e:
                logger.exception(f"Failed to close trade for user {user_id}")
                return
                
# === main.py (Lines 2001–2500) ===

# === Telegram Auto Bot Commands ===

async def set_autobot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args

    if len(args) != 5:
        await update.message.reply_text("Usage: /set_autobot <symbol> <timeframe> <risk%> <TP%> <SL%>")
        return

    symbol, tf, risk, tp, sl = args
    update_user_data(user_id, {
        "auto_bot": {
            "enabled": True,
            "symbol": symbol.upper(),
            "timeframe": tf,
            "risk_percent": float(risk),
            "take_profit": float(tp),
            "stop_loss": float(sl),
            "strategy": "sma"
        }
    })

    await update.message.reply_text("Auto Bot strategy saved and enabled.")

async def toggle_autobot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)
    current = user_data.get("auto_bot", {}).get("enabled", False)
    new_val = not current
    update_user_data(user_id, {"auto_bot/enabled": new_val})
    await update.message.reply_text(f"Auto Bot is now {'enabled' if new_val else 'disabled'}.")

async def autobot_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)
    bot_data = user_data.get("auto_bot", {})
    if not bot_data:
        await update.message.reply_text("Auto Bot not configured. Use /set_autobot.")
    else:
        text = json.dumps(bot_data, indent=2)
        await update.message.reply_text(f"Current Auto Bot setup:\n<pre>{text}</pre>", parse_mode="HTML")

# === Scheduled Bot Runner ===

def run_all_bots():
    users_ref = db.reference("users")
    users = users_ref.get() or {}

    for user_id, user_data in users.items():
        if str(user_id) not in AUTO_BOT_ACTIVE:
            AUTO_BOT_ACTIVE[str(user_id)] = True
            threading.Thread(target=run_autobot_for_user, args=(user_id, user_data)).start()

    # Re-run after interval
    threading.Timer(AUTO_BOT_INTERVAL, run_all_bots).start()

# === Edge AI Placeholder ===

def get_edge_ai_signal(symbol, interval):
    # Future AI model hook
    return "HOLD"

def apply_ai_strategy(user_data):
    signal = get_edge_ai_signal(user_data["auto_bot"]["symbol"], user_data["auto_bot"]["timeframe"])
    logger.info(f"[AI] Signal for user {user_data['user_id']}: {signal}")
    # Currently unused, to be implemented

# === Extend Bot Commands ===

telegram_app.add_handler(CommandHandler("set_autobot", set_autobot))
telegram_app.add_handler(CommandHandler("toggle_autobot", toggle_autobot))
telegram_app.add_handler(CommandHandler("autobot_status", autobot_status))

# === main.py (Lines 2501–2600+) ===

# === Firebase Stats + Trade Tracking ===

def calculate_user_stats(user_id):
    trades = db.reference(f"trades/{user_id}").get() or {}
    profit_total = 0
    wins = 0
    losses = 0
    trade_count = 0

    for _, t in trades.items():
        if "profit" in t:
            p = float(t["profit"])
            profit_total += p
            if p >= 0:
                wins += 1
            else:
                losses += 1
        trade_count += 1

    win_rate = (wins / trade_count) * 100 if trade_count else 0
    update_user_data(user_id, {
        "stats": {
            "profit": round(profit_total, 2),
            "trades": trade_count,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 2)
        }
    })

def trade_summary(user_id):
    stats = get_user_data(user_id).get("stats", {})
    return f"""
Total Profit: {stats.get('profit', 0)}
Trades: {stats.get('trades', 0)}
Wins: {stats.get('wins', 0)}
Losses: {stats.get('losses', 0)}
Win Rate: {stats.get('win_rate', 0)}%
"""

async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    calculate_user_stats(user_id)
    summary = trade_summary(user_id)
    await update.message.reply_text(summary)

telegram_app.add_handler(CommandHandler("mystats", my_stats))

# === Safety Checks ===

def validate_user_config(user_data):
    required = ["exchange", "api_key", "api_secret"]
    return all(user_data.get(k) for k in required)

# === Final Start Function ===
def main():
    logger.info("Starting bot...")
    run_all_bots()

    port = int(os.getenv("PORT", 8443))
    webhook_url = os.getenv("WEBHOOK_URL")

    telegram_app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=os.getenv("BOT_TOKEN"),
        webhook_url=f"{webhook_url}/{os.getenv('BOT_TOKEN')}"
    )

if __name__ == "__main__":
    main()
    
   
