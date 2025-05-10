import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, db
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Firebase Initialization
firebase_json = os.getenv("FIREBASE_CREDENTIALS")
if not firebase_json:
    raise ValueError("FIREBASE_CREDENTIALS not set")

cred = credentials.Certificate(json.loads(firebase_json))
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://your-database-url.firebaseio.com/'
})

# Telegram Bot Setup
telegram_bot_token = os.getenv("BOT_TOKEN")
if not telegram_bot_token:
    raise ValueError("BOT_TOKEN not set")

telegram_app = Application.builder().token(telegram_bot_token).build()

# Firebase Database Reference Functions
def get_user_data(telegram_id):
    ref = db.reference(f"users/{telegram_id}")
    return ref.get()

def update_user_data(telegram_id, data):
    ref = db.reference(f"users/{telegram_id}")
    ref.update(data)

# Helper function for adding trade data
def save_trade(telegram_id, trade_data):
    ref = db.reference(f"trades/{telegram_id}")
    ref.push(trade_data)

# Encryption Setup (optional if you're encrypting sensitive data)
SECRET_KEY = os.getenv("SECRET_KEY")
if SECRET_KEY:
    from cryptography.fernet import Fernet
    fernet = Fernet(SECRET_KEY)

# Set up logging for debugging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample Commands to get started
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to Crypto Bot! Type /help for command info.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    /start - Start the bot
    /help - Show this help message
    /register - Register with your API keys
    /balance - View your trading balance
    """
    await update.message.reply_text(help_text)

# Handle user registration and API key linking
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if len(context.args) != 2:
        await update.message.reply_text("Please provide both Binance API key and secret. Usage: /register <API_KEY> <API_SECRET>")
        return

    binance_api_key = context.args[0]
    binance_api_secret = context.args[1]

    # Store the API keys securely in Firebase under the user
    update_user_data(user_id, {
        'binance_api_key': binance_api_key,
        'binance_api_secret': binance_api_secret
    })

    await update.message.reply_text("Your API keys have been registered successfully!")

# Fetch and display balance for registered users
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Example: Use the Binance API to fetch the user's balance
    from binance.client import Client
    client = Client(user_data['binance_api_key'], user_data['binance_api_secret'])
    balance = client.get_account()

    # Show a summary of the balance
    balances = "\n".join([f"{b['asset']}: {b['free']}" for b in balance['balances']])
    await update.message.reply_text(f"Your current balance:\n{balances}")

# Simple trade execution logic (buy/sell)
async def execute_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    if len(context.args) != 3:
        await update.message.reply_text("Usage: /trade <BUY/SELL> <SYMBOL> <AMOUNT>")
        return

    action = context.args[0].upper()
    symbol = context.args[1].upper()
    amount = float(context.args[2])

    if action not in ['BUY', 'SELL']:
        await update.message.reply_text("Invalid action. Please use BUY or SELL.")
        return

    # Initialize Binance client
    from binance.client import Client
    client = Client(user_data['binance_api_key'], user_data['binance_api_secret'])

    try:
        if action == "BUY":
            order = client.order_market_buy(symbol=symbol, quantity=amount)
        elif action == "SELL":
            order = client.order_market_sell(symbol=symbol, quantity=amount)

        # Store the trade data in Firebase
        trade_data = {
            'symbol': symbol,
            'amount': amount,
            'price': order['fills'][0]['price'],
            'action': action,
            'time': str(datetime.now())
        }
        save_trade(user_id, trade_data)

        await update.message.reply_text(f"Trade executed: {action} {amount} {symbol} at {trade_data['price']}")

    except Exception as e:
        await update.message.reply_text(f"Error executing trade: {e}")

# Tournament management logic (example for weekly leaderboard)
async def tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Here we can simulate trading performance and calculate user rank
    # Simulate some kind of performance
    performance_score = 100  # Example score, replace with actual trade logic

    # Add or update performance score in the leaderboard (Firebase)
    leaderboard_ref = db.reference("leaderboard")
    leaderboard = leaderboard_ref.get() or {}
    leaderboard[user_id] = performance_score
    leaderboard_ref.set(leaderboard)

    # Show leaderboard (Top 10 players)
    top_players = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)[:10]
    leaderboard_msg = "\n".join([f"{i+1}. {user_id} - {score}" for i, (user_id, score) in enumerate(top_players)])
    await update.message.reply_text(f"Current Tournament Leaderboard:\n{leaderboard_msg}")

# Example AI-based advice for users
async def edge_ai_advice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Example: Calculate profit/loss based on recent trades
    recent_trades = db.reference(f"trades/{user_id}").get() or {}

    if not recent_trades:
        await update.message.reply_text("No trades found for analysis.")
        return

    total_profit = sum([trade['profit'] for trade in recent_trades.values()])
    advice = "Keep pushing, but consider taking profits after a certain threshold!"

    # AI coaching message
    if total_profit > 0:
        advice = f"You're doing great! Total profit: {total_profit}. {advice}"

    await update.message.reply_text(f"Edge AI Advice: {advice}")

# Handle tournament resets every 6 months and distribute rewards
async def tournament_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get leaderboard and calculate season reset rewards
    leaderboard_ref = db.reference("leaderboard")
    leaderboard = leaderboard_ref.get() or {}

    # Sort leaderboard by performance score (Descending order)
    sorted_leaderboard = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)

    # Allocate rewards (you can adjust this logic based on your prize pool distribution)
    total_tournament_pot = 100000  # Example value, replace with actual prize pool
    reward_per_player = total_tournament_pot // len(sorted_leaderboard)

    # Distribute rewards
    for i, (user_id, score) in enumerate(sorted_leaderboard):
        reward = reward_per_player
        # Optional: Give higher rewards for top performers
        if i < 10:
            reward += 1000  # Extra reward for top 10 players

        # Store the seasonal reset reward data
        user_data = get_user_data(user_id)
        updated_rewards = user_data.get('rewards', 0) + reward
        update_user_data(user_id, {'rewards': updated_rewards})

    # Reset leaderboard for the next season
    leaderboard_ref.set({})
    await update.message.reply_text("Tournament reset complete! Rewards have been distributed.")

# Edge AI emotional coaching
async def edge_ai_emotional_coaching(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Example: Emotional state based on recent trade history
    recent_trades = db.reference(f"trades/{user_id}").get() or {}

    if not recent_trades:
        await update.message.reply_text("No trades found for analysis.")
        return

    losses = sum([trade['loss'] for trade in recent_trades.values()])
    profit = sum([trade['profit'] for trade in recent_trades.values()])

    # Analyze emotional state based on profits and losses
    emotional_state = ""
    if losses > profit:
        emotional_state = "It seems you're feeling the pressure from losses. Take a step back and consider a more conservative strategy."
    elif profit > losses:
        emotional_state = "You're in a good state of profit! Stay disciplined and avoid overtrading."
    else:
        emotional_state = "You're balancing losses and gains. Try to focus on improving your strategy."

    # Send coaching advice based on emotional state
    await update.message.reply_text(f"Edge AI Emotional Coaching: {emotional_state}")

# Track and send alerts when user reaches profit targets
async def track_profit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Example: Track user balance change over time (Profit/Loss)
    initial_balance = user_data.get('initial_balance', 1000)  # Assuming the initial balance is set during registration
    current_balance = user_data.get('current_balance', initial_balance)

    profit = current_balance - initial_balance
    profit_target = 100  # Example target, can be dynamic or set by user

    # Send alert if the user reaches their profit target
    if profit >= profit_target:
        await update.message.reply_text(f"Congratulations! You've reached your profit target of {profit_target} ZAR! Total profit: {profit} ZAR")

    # Update current balance in Firebase
    update_user_data(user_id, {'current_balance': current_balance})

# Display user's trade history and performance
async def trade_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Fetch trade data
    trades_ref = db.reference(f"trades/{user_id}")
    trades = trades_ref.get()

    if not trades:
        await update.message.reply_text("No trades found.")
        return

    # Display trade history
    trade_history_message = "Your Trade History:\n"
    for trade_id, trade_data in trades.items():
        trade_history_message += f"ID: {trade_id}\n"
        trade_history_message += f"Symbol: {trade_data['symbol']}, Amount: {trade_data['amount']}, Price: {trade_data['price']}\n"
        trade_history_message += f"Action: {trade_data['action']}, Profit: {trade_data['profit']}, Loss: {trade_data['loss']}\n\n"

    await update.message.reply_text(trade_history_message)

# Monthly leaderboard reset and prize distribution
async def monthly_leaderboard_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leaderboard_ref = db.reference("leaderboard")
    leaderboard = leaderboard_ref.get() or {}

    # Sort leaderboard by performance score (Descending order)
    sorted_leaderboard = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)

    # Allocate rewards for the top players
    total_monthly_prize_pool = 50000  # Example monthly prize pool value
    monthly_reward_per_player = total_monthly_prize_pool // len(sorted_leaderboard)

    for i, (user_id, score) in enumerate(sorted_leaderboard):
        reward = monthly_reward_per_player
        # Optional: Extra rewards for top 5 players
        if i < 5:
            reward += 500

        # Store rewards in user's data
        user_data = get_user_data(user_id)
        updated_rewards = user_data.get('rewards', 0) + reward
        update_user_data(user_id, {'rewards': updated_rewards})

    # Reset leaderboard for next month
    leaderboard_ref.set({})
    await update.message.reply_text("Monthly leaderboard reset complete! Rewards distributed to top players.")

# Send alerts when a trade hits stop-loss or take-profit points
async def trade_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Fetch the user's trade status
    trade_ref = db.reference(f"trades/{user_id}")
    trades = trade_ref.get()

    if not trades:
        await update.message.reply_text("No trades in progress.")
        return

    # Check each trade's status
    for trade_id, trade_data in trades.items():
        current_price = get_current_price(trade_data['symbol'])  # Example function to get live price
        stop_loss = trade_data.get('stop_loss')
        take_profit = trade_data.get('take_profit')

        # Check if price hits stop-loss or take-profit
        if stop_loss and current_price <= stop_loss:
            await update.message.reply_text(f"Stop-Loss Triggered: Trade ID {trade_id} has hit your stop-loss!")
            # Optional: Automatically close the trade if needed
            close_trade(user_id, trade_id)

        if take_profit and current_price >= take_profit:
            await update.message.reply_text(f"Take-Profit Triggered: Trade ID {trade_id} has hit your take-profit!")
            # Optional: Automatically close the trade if needed
            close_trade(user_id, trade_id)

# Function to get the current price of a trading pair
def get_current_price(symbol):
    # Placeholder function for live price fetching from Binance or Luno
    # You should implement Binance API or Luno API calls to get real-time price data
    # Example for Binance API:
    # response = binance_client.get_symbol_ticker(symbol=symbol)
    # return response['price']

    # Simulating a price fetch for now
    return 10000  # Example price for a symbol

# Function to allow users to set custom alerts for price changes
async def set_price_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Get price alert settings from the user
    try:
        target_price = float(context.args[0])  # Expecting the target price in args
        symbol = context.args[1]  # Expecting the symbol like 'BTCUSDT'
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /set_price_alert <price> <symbol>")
        return

    # Store the alert in the database
    price_alert_ref = db.reference(f"price_alerts/{user_id}")
    price_alert_ref.set({'target_price': target_price, 'symbol': symbol})

    await update.message.reply_text(f"Price alert set! You'll be notified when {symbol} reaches {target_price}.")

# Function to automatically execute trades based on a given strategy
async def auto_trade_execution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Example: Check user’s balance and decide whether to trade
    balance = get_user_balance(user_id)  # Implement this to fetch user balance from Binance API
    risk_percentage = 0.02  # Risk 2% of the balance for each trade

    trade_amount = balance * risk_percentage
    symbol = "BTCUSDT"  # Example trading pair

    # Example of auto-buy logic (simplified)
    if balance >= trade_amount:
        order = execute_trade(symbol, trade_amount)
        await update.message.reply_text(f"Executing auto-trade: {order}")
    else:
        await update.message.reply_text("Insufficient balance for trade.")
    
def execute_trade(symbol, amount):
    # Placeholder function to execute trade
    # You should implement Binance API calls to place the order
    # Example: binance_client.order_market_buy(symbol=symbol, quantity=amount)
    return f"Order placed for {amount} of {symbol}"

# Function to analyze the user's trading behavior
async def behavioral_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Analyze recent trade history for patterns
    trades_ref = db.reference(f"trades/{user_id}")
    trades = trades_ref.get()

    if not trades:
        await update.message.reply_text("No trades found for analysis.")
        return

    # Example: Analyze if the user is overtrading
    trade_count = len(trades)
    overtrading_threshold = 10  # Example threshold

    if trade_count > overtrading_threshold:
        await update.message.reply_text("Warning: You are trading too frequently! Consider reviewing your strategy.")
    else:
        await update.message.reply_text("Your trade frequency looks balanced. Keep it up!")

# Update leaderboard dynamically based on user performance
async def update_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Calculate user performance (profit, trade success rate, etc.)
    performance_score = calculate_performance_score(user_id)  # You need to define this based on your criteria

    # Update leaderboard
    leaderboard_ref = db.reference("leaderboard")
    leaderboard = leaderboard_ref.get() or {}

    # Add or update user performance in the leaderboard
    leaderboard[user_id] = performance_score
    leaderboard_ref.set(leaderboard)

    await update.message.reply_text(f"Your performance has been updated! Current leaderboard score: {performance_score}")

def calculate_performance_score(user_id):
    # Placeholder function for calculating performance score
    # You should implement logic to calculate the score based on user performance
    return 100  # Example score

# Enable trade simulation for users to test strategies without real money
async def trade_simulation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Start a simulation mode (user will not be trading with real funds)
    simulation_balance = 10000  # Example starting balance for simulation
    user_data['simulation_mode'] = True  # Flag to indicate the user is in simulation mode
    update_user_data(user_id, user_data)

    await update.message.reply_text("You are now in trade simulation mode! You can test your strategies without real money.")

# Simulate a trade execution in simulation mode
async def simulate_trade_execution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if user_data.get('simulation_mode', False):
        # Execute trade using the simulated balance
        trade_amount = 1000  # Example amount to trade
        simulation_balance = user_data.get('simulation_balance', 10000)

        if simulation_balance >= trade_amount:
            new_balance = simulation_balance - trade_amount
            user_data['simulation_balance'] = new_balance
            update_user_data(user_id, user_data)

            await update.message.reply_text(f"Simulated trade executed! New simulated balance: {new_balance}")
        else:
            await update.message.reply_text("Insufficient funds in simulation mode.")
    else:
        await update.message.reply_text("You need to enter simulation mode first using /trade_simulation.")

# Function to display portfolio balance and individual asset performance
async def show_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Fetch user's portfolio data from Binance API (or simulate it for now)
    portfolio_data = get_user_portfolio(user_data['binance_api_key'])

    # Display user's portfolio performance
    portfolio_message = "Your Portfolio:\n"
    for asset, data in portfolio_data.items():
        portfolio_message += f"{asset}: {data['quantity']} - Value: {data['value']} USD\n"

    # Display total portfolio value and profit/loss
    total_value = sum([data['value'] for data in portfolio_data.values()])
    profit_loss = total_value - user_data['initial_balance']
    portfolio_message += f"Total Value: {total_value} USD\n"
    portfolio_message += f"Profit/Loss: {profit_loss} USD\n"

    await update.message.reply_text(portfolio_message)

def get_user_portfolio(api_key):
    # Placeholder function to fetch portfolio data from Binance or other exchanges
    # In a real implementation, use Binance API to fetch user's portfolio
    return {
        'BTC': {'quantity': 0.5, 'value': 25000},
        'ETH': {'quantity': 10, 'value': 20000},
        'USDT': {'quantity': 1000, 'value': 1000}
    }

# Function to allow users to define custom trading strategies
async def set_custom_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Expecting strategy parameters from the user
    try:
        strategy_type = context.args[0]  # Example: 'MACD' or 'RSI'
        entry_condition = context.args[1]  # Example: 'crosses above 50'
        exit_condition = context.args[2]  # Example: 'crosses below 50'
    except IndexError:
        await update.message.reply_text("Usage: /set_strategy <strategy_type> <entry_condition> <exit_condition>")
        return

    # Save the strategy to the database
    strategy_ref = db.reference(f"strategies/{user_id}")
    strategy_ref.set({'strategy_type': strategy_type, 'entry_condition': entry_condition, 'exit_condition': exit_condition})

    await update.message.reply_text(f"Custom strategy set! Type: {strategy_type}, Entry: {entry_condition}, Exit: {exit_condition}")

# Function to evaluate custom strategy conditions during each trade
def evaluate_strategy(symbol, user_data):
    strategy_ref = db.reference(f"strategies/{user_data['telegram_id']}")
    strategy = strategy_ref.get()

    if not strategy:
        return False  # No strategy set

    # Example: Evaluate entry condition based on market data (e.g., MACD, RSI)
    entry_condition = strategy.get('entry_condition')
    if entry_condition == 'crosses above 50':  # Placeholder condition for testing
        current_indicator_value = get_current_indicator_value(symbol)  # Placeholder for MACD or RSI value
        if current_indicator_value > 50:
            return True  # Entry condition met

    return False

def get_current_indicator_value(symbol):
    # Placeholder function for fetching market indicator value (e.g., MACD, RSI)
    return 60  # Example value

# Function to execute trades based on custom strategy
async def execute_strategy_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Get the custom strategy for the user
    strategy_ref = db.reference(f"strategies/{user_id}")
    strategy = strategy_ref.get()

    if not strategy:
        await update.message.reply_text("You don't have a custom strategy set.")
        return

    symbol = "BTCUSDT"  # Example symbol
    trade_amount = 1000  # Example trade amount

    # Check if the strategy's entry condition is met
    if evaluate_strategy(symbol, user_data):
        order = execute_trade(symbol, trade_amount)
        await update.message.reply_text(f"Strategy triggered: {order}")
    else:
        await update.message.reply_text("Strategy conditions not met. No trade executed.")

# Function to track and close trades
async def monitor_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    trade_ref = db.reference(f"trades/{user_id}")
    trades = trade_ref.get()

    if not trades:
        await update.message.reply_text("No trades in progress.")
        return

    # Check for open trades and close them if certain conditions are met
    for trade_id, trade_data in trades.items():
        current_price = get_current_price(trade_data['symbol'])

        if current_price >= trade_data['take_profit']:
            close_trade(user_id, trade_id)
            await update.message.reply_text(f"Take-profit reached. Trade {trade_id} closed.")
        elif current_price <= trade_data['stop_loss']:
            close_trade(user_id, trade_id)
            await update.message.reply_text(f"Stop-loss reached. Trade {trade_id} closed.")

def close_trade(user_id, trade_id):
    # Placeholder function to close the trade
    # You should implement Binance API call to cancel or close the trade
    return f"Trade {trade_id} closed for user {user_id}"

# Function to display advanced user analytics
async def show_user_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Fetch user’s trade history and performance
    trade_history = get_user_trade_history(user_id)

    if not trade_history:
        await update.message.reply_text("No trade history found.")
        return

    # Calculate total profit/loss and win rate
    total_profit = sum([trade['profit'] for trade in trade_history])
    total_trades = len(trade_history)
    win_rate = sum([1 for trade in trade_history if trade['profit'] > 0]) / total_trades * 100

    analytics_message = f"User Analytics:\nTotal Profit/Loss: {total_profit} USD\n"
    analytics_message += f"Total Trades: {total_trades}\nWin Rate: {win_rate}%"

    await update.message.reply_text(analytics_message)

def get_user_trade_history(user_id):
    # Placeholder function to fetch trade history from the database
    return [
        {'trade_id': 1, 'profit': 500},
        {'trade_id': 2, 'profit': -200},
        {'trade_id': 3, 'profit': 300}
    ]

# Function to set stop-loss and take-profit orders automatically
async def set_auto_stop_loss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    try:
        stop_loss_price = float(context.args[0])
        take_profit_price = float(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /set_auto_stop_loss <stop_loss_price> <take_profit_price>")
        return

    # Save the stop-loss and take-profit to the database for later use
    stop_loss_ref = db.reference(f"stop_loss/{user_id}")
    stop_loss_ref.set({'stop_loss': stop_loss_price, 'take_profit': take_profit_price})

    await update.message.reply_text(f"Stop-loss and take-profit set! Stop-Loss: {stop_loss_price}, Take-Profit: {take_profit_price}")

# Function to set up real-time price monitoring and alerts for a specific asset
async def set_price_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    try:
        symbol = context.args[0]  # Example: 'BTCUSDT'
        alert_price = float(context.args[1])  # Price to trigger the alert
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /set_price_alert <symbol> <alert_price>")
        return

    # Save the price alert to the database
    alert_ref = db.reference(f"price_alerts/{user_id}")
    alert_ref.set({'symbol': symbol, 'alert_price': alert_price})

    await update.message.reply_text(f"Price alert set for {symbol} at {alert_price} USD.")

# Function to monitor the prices and send alerts
def monitor_price_alerts():
    # Placeholder function for real-time price monitoring
    # Fetch all price alerts from the database
    price_alerts_ref = db.reference("price_alerts")
    price_alerts = price_alerts_ref.get()

    if not price_alerts:
        return

    # Check if any alerts are triggered
    for user_id, alerts in price_alerts.items():
        for alert in alerts:
            current_price = get_current_price(alert['symbol'])
            if current_price >= alert['alert_price']:
                send_price_alert(user_id, alert['symbol'], current_price)

def get_current_price(symbol):
    # Placeholder function to fetch the current price of an asset
    return 60000  # Example price, this should be fetched from Binance or other exchange API

def send_price_alert(user_id, symbol, current_price):
    # Function to send a price alert to the user
    user_telegram_id = get_user_telegram_id(user_id)
    message = f"Price Alert! {symbol} has reached {current_price} USD."
    send_telegram_message(user_telegram_id, message)

def send_telegram_message(user_telegram_id, message):
    # Send the message to the user's Telegram account
    context.bot.send_message(chat_id=user_telegram_id, text=message)

def get_user_telegram_id(user_id):
    # Function to get the user's Telegram ID from the database
    return db.reference(f"users/{user_id}/telegram_id").get()

# Function to review trade history for performance analysis
async def review_trade_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Fetch trade history from the database
    trade_history_ref = db.reference(f"trades/{user_id}")
    trade_history = trade_history_ref.get()

    if not trade_history:
        await update.message.reply_text("You have no trade history.")
        return

    # Summarize the trade history
    trade_summary = "Your Trade History:\n"
    total_profit = 0
    win_count = 0
    loss_count = 0

    for trade in trade_history:
        profit = trade.get('profit', 0)
        total_profit += profit
        if profit > 0:
            win_count += 1
        elif profit < 0:
            loss_count += 1

        trade_summary += f"Trade {trade['trade_id']}: {profit} USD\n"

    # Provide a detailed summary
    trade_summary += f"\nTotal Profit: {total_profit} USD\n"
    trade_summary += f"Win Rate: {win_count / len(trade_history) * 100}%\n"
    trade_summary += f"Loss Rate: {loss_count / len(trade_history) * 100}%\n"

    await update.message.reply_text(trade_summary)

# Function to track user progress and achievements
async def track_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Track achievements based on trading milestones
    achievements = get_user_achievements(user_id)

    achievements_message = "Your Achievements:\n"
    for achievement in achievements:
        achievements_message += f"{achievement['name']}: {achievement['status']}\n"

    await update.message.reply_text(achievements_message)

def get_user_achievements(user_id):
    # Placeholder function to fetch user achievements
    return [
        {'name': 'First Trade', 'status': 'Completed'},
        {'name': '1000 USD Profit', 'status': 'In Progress'},
        {'name': 'Risk-Free Trader', 'status': 'Unlocked'}
    ]

# Function to track and display bot performance metrics
async def show_bot_performance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Bot performance metrics to be tracked (e.g., success rate, trades executed, total profits)
    performance_data = get_bot_performance()

    performance_message = "Bot Performance Metrics:\n"
    performance_message += f"Total Trades Executed: {performance_data['total_trades']}\n"
    performance_message += f"Successful Trades: {performance_data['successful_trades']}\n"
    performance_message += f"Success Rate: {performance_data['success_rate']}%\n"
    performance_message += f"Total Profit: {performance_data['total_profit']} USD\n"

    await update.message.reply_text(performance_message)

def get_bot_performance():
    # Placeholder function for fetching bot performance data
    return {
        'total_trades': 150,
        'successful_trades': 120,
        'success_rate': 80,
        'total_profit': 5000
    }

# Function to schedule trades at specific times
async def schedule_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    try:
        trade_time = context.args[0]  # Format: 'HH:MM'
        symbol = context.args[1]  # Symbol to trade, e.g., 'BTCUSDT'
        amount = float(context.args[2])  # Amount to trade
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /schedule_trade <HH:MM> <symbol> <amount>")
        return

    # Convert the time to seconds since midnight for scheduling
    scheduled_time = convert_to_seconds(trade_time)
    scheduled_trade_ref = db.reference(f"scheduled_trades/{user_id}")
    scheduled_trade_ref.set({'time': scheduled_time, 'symbol': symbol, 'amount': amount})

    await update.message.reply_text(f"Trade scheduled at {trade_time} for {amount} {symbol}.")

def convert_to_seconds(time_str):
    # Convert 'HH:MM' to seconds since midnight
    hours, minutes = map(int, time_str.split(":"))
    return hours * 3600 + minutes * 60

# Function to execute scheduled trades at the correct time
def execute_scheduled_trades():
    # Placeholder function to execute scheduled trades at the right time
    scheduled_trades_ref = db.reference("scheduled_trades")
    scheduled_trades = scheduled_trades_ref.get()

    for user_id, trades in scheduled_trades.items():
        for trade in trades:
            if check_if_trade_time(trade['time']):
                execute_trade(trade['symbol'], trade['amount'])

def check_if_trade_time(scheduled_time):
    # Placeholder check function for trade timing
    current_time = time.time()
    return current_time >= scheduled_time

# Function to provide feedback on trade execution
async def trade_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    trade_id = context.args[0]  # Trade ID to fetch feedback for
    trade_feedback = get_trade_feedback(user_id, trade_id)

    if not trade_feedback:
        await update.message.reply_text("No feedback available for this trade.")
        return

    await update.message.reply_text(f"Trade Feedback for Trade {trade_id}: {trade_feedback}")

def get_trade_feedback(user_id, trade_id):
    # Placeholder function to fetch trade feedback
    return "Trade executed successfully. Profit: 150 USD."

# Function to calculate trade risk based on the user's balance and chosen trade parameters
def calculate_trade_risk(user_balance, trade_amount):
    # Placeholder for risk management logic
    risk_factor = 0.02  # Example: 2% of the balance can be risked per trade
    max_risk = user_balance * risk_factor

    if trade_amount > max_risk:
        return False, max_risk
    return True, max_risk

# Function to execute a trade with risk management checks
async def execute_trade_with_risk_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    try:
        symbol = context.args[0]  # Symbol to trade (e.g., 'BTCUSDT')
        amount = float(context.args[1])  # Amount to trade
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /execute_trade <symbol> <amount>")
        return

    # Fetch the user's balance
    user_balance = get_user_balance(user_id)

    # Risk check before executing the trade
    is_safe, max_risk = calculate_trade_risk(user_balance, amount)
    if not is_safe:
        await update.message.reply_text(f"Risk too high! You can only risk up to {max_risk} USD per trade.")
        return

    # Proceed with the trade execution
    trade_successful = execute_trade(symbol, amount)

    if trade_successful:
        await update.message.reply_text(f"Trade executed successfully for {amount} {symbol}.")
    else:
        await update.message.reply_text("Trade execution failed. Please try again.")

def get_user_balance(user_id):
    # Placeholder function to fetch user balance from the exchange
    return 1000  # Example balance in USD

def execute_trade(symbol, amount):
    # Placeholder function to execute the trade on the exchange
    # This should interface with Binance API or similar exchange APIs
    return True  # Return True if the trade was successful

# Function to analyze the performance of a given strategy
def analyze_strategy_performance(strategy_data):
    # Example analysis of strategy performance (win rate, average profit per trade, etc.)
    total_trades = len(strategy_data)
    successful_trades = sum(1 for trade in strategy_data if trade['profit'] > 0)
    total_profit = sum(trade['profit'] for trade in strategy_data)

    win_rate = (successful_trades / total_trades) * 100 if total_trades > 0 else 0
    average_profit = total_profit / total_trades if total_trades > 0 else 0

    return {
        'win_rate': win_rate,
        'average_profit': average_profit,
        'total_trades': total_trades,
        'total_profit': total_profit
    }

# Function to suggest strategy improvements based on performance
async def suggest_strategy_improvements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Fetch strategy performance data from the database
    strategy_data = get_strategy_performance(user_id)

    if not strategy_data:
        await update.message.reply_text("No strategy performance data available.")
        return

    performance_metrics = analyze_strategy_performance(strategy_data)

    # Provide the user with strategy feedback
    performance_feedback = f"Strategy Performance:\n"
    performance_feedback += f"Win Rate: {performance_metrics['win_rate']}%\n"
    performance_feedback += f"Average Profit: {performance_metrics['average_profit']} USD\n"
    performance_feedback += f"Total Trades: {performance_metrics['total_trades']}\n"
    performance_feedback += f"Total Profit: {performance_metrics['total_profit']} USD\n"

    # Suggest improvements if necessary
    if performance_metrics['win_rate'] < 60:
        performance_feedback += "\nYour strategy's win rate is low. Consider adjusting your risk management or entry/exit points."

    await update.message.reply_text(performance_feedback)

def get_strategy_performance(user_id):
    # Placeholder function to fetch the user's strategy performance data from the database
    return [
        {'profit': 50}, {'profit': -10}, {'profit': 100}, {'profit': 20}, {'profit': -5}
    ]

# Function to send personalized trade suggestions and market alerts
async def send_trade_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Example trade suggestions based on market trends (should integrate with market data)
    trade_suggestions = [
        {"symbol": "BTCUSDT", "suggestion": "Buy", "target_price": 65000},
        {"symbol": "ETHUSDT", "suggestion": "Sell", "target_price": 4000},
    ]

    suggestion_message = "Trade Suggestions:\n"
    for suggestion in trade_suggestions:
        suggestion_message += f"{suggestion['symbol']}: {suggestion['suggestion']} (Target: {suggestion['target_price']} USD)\n"

    await update.message.reply_text(suggestion_message)

# Function to send periodic market updates to users
def send_periodic_market_update():
    # Placeholder function to send market updates to users periodically
    market_update = "Market Update: BTC has increased by 5% today. Consider reviewing your positions."
    
    # Fetch all users from the database and send the update
    all_users = get_all_users()
    for user in all_users:
        send_telegram_message(user['telegram_id'], market_update)

def get_all_users():
    # Placeholder function to fetch all users from the database
    return [
        {"telegram_id": "123456789"},
        {"telegram_id": "987654321"}
    ]

# Function to generate trade entry signals based on simple moving average (SMA)
def generate_trade_signal(symbol):
    # Example using SMA as a strategy for generating trade signals
    prices = get_historical_prices(symbol)
    short_sma = sum(prices[-10:]) / 10  # Last 10 prices
    long_sma = sum(prices[-50:]) / 50   # Last 50 prices

    if short_sma > long_sma:
        return "Buy"
    elif short_sma < long_sma:
        return "Sell"
    return "Hold"

def get_historical_prices(symbol):
    # Placeholder for fetching historical prices from the exchange
    return [60000, 60500, 61000, 61500, 62000, 62500, 63000, 63500, 64000, 64500]  # Example price data

# Function to notify users when a signal is generated
async def send_trade_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    try:
        symbol = context.args[0]  # Symbol to generate signal for (e.g., 'BTCUSDT')
    except IndexError:
        await update.message.reply_text("Usage: /send_trade_signal <symbol>")
        return

    # Generate the trade signal
    signal = generate_trade_signal(symbol)
    await update.message.reply_text(f"Trade Signal for {symbol}: {signal}")

# Function to handle errors gracefully and provide user-friendly messages
async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Try to execute the command
        await execute_trade_with_risk_management(update, context)
    except Exception as e:
        # Log the error and send a user-friendly message
        logging.error(f"Error occurred: {e}")
        await update.message.reply_text("An error occurred while processing your request. Please try again later.")

# Function to automatically restart the bot in case of failures (resilience)
def restart_bot():
    # Placeholder function to restart the bot (e.g., if running on a server)
    logging.info("Bot is restarting due to a failure...")
    os.execv(sys.executable, ['python'] + sys.argv)

# Function to fetch leaderboard standings
async def get_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = get_top_users_by_profit()
    leaderboard_text = "Top Traders Leaderboard:\n\n"

    for idx, user in enumerate(top_users, start=1):
        leaderboard_text += f"{idx}. {user['username']} - Profit: ${user['total_profit']:.2f}, Trophies: {user['trophies']}\n"

    await update.message.reply_text(leaderboard_text)

def get_top_users_by_profit(limit=10):
    # Placeholder: Fetch top users based on total profit and trophies
    return [
        {"username": "trader1", "total_profit": 2500.50, "trophies": 3},
        {"username": "trader2", "total_profit": 2300.00, "trophies": 2},
        {"username": "trader3", "total_profit": 2100.75, "trophies": 1},
    ][:limit]

# Function to award trophies based on periodic performance
def award_trophies():
    users = get_all_users()
    for user in users:
        user_profit = calculate_user_profit(user['telegram_id'])
        if user_profit > 1000:  # Example threshold
            increment_user_trophies(user['telegram_id'])

def calculate_user_profit(user_id):
    # Placeholder for calculating total profit from trades
    return 1500  # Example

def increment_user_trophies(user_id):
    # Add 1 trophy to the user's Firebase record
    user_ref = db.collection("users").document(str(user_id))
    user_doc = user_ref.get()
    if user_doc.exists:
        current_trophies = user_doc.to_dict().get("trophies", 0)
        user_ref.update({"trophies": current_trophies + 1})

# Function to simulate a tournament payout to top 100 players
def distribute_tournament_rewards():
    prize_pool = calculate_total_prize_pool()
    top_players = get_top_users_by_profit(limit=100)

    for rank, user in enumerate(top_players, start=1):
        payout = calculate_tiered_payout(rank, prize_pool)
        credit_user_account(user['telegram_id'], payout)

def calculate_total_prize_pool():
    # Example: 1% of all user profits go into the prize pool
    return 5000.00  # Placeholder amount

def calculate_tiered_payout(rank, total_pool):
    if rank == 1:
        return total_pool * 0.25
    elif rank <= 5:
        return total_pool * 0.15 / 4
    elif rank <= 20:
        return total_pool * 0.30 / 15
    else:
        return total_pool * 0.30 / 80

def credit_user_account(user_id, amount):
    user_ref = db.collection("users").document(str(user_id))
    user_doc = user_ref.get()
    if user_doc.exists:
        current_balance = user_doc.to_dict().get("reward_balance", 0)
        user_ref.update({"reward_balance": current_balance + amount})

# Function to deduct 1.25% tournament fee from profitable trades
def deduct_tournament_fee(user_id, profit):
    if profit <= 0:
        return

    tournament_cut = profit * 0.0125
    app_fee = profit * 0.0025
    pool_fee = profit * 0.007
    reset_fee = profit * 0.003

    record_fee_distribution(user_id, app_fee, pool_fee, reset_fee)

def record_fee_distribution(user_id, app_fee, pool_fee, reset_fee):
    fee_data = {
        "app_fee": app_fee,
        "pool_fee": pool_fee,
        "reset_fee": reset_fee,
        "timestamp": datetime.utcnow()
    }
    db.collection("fees").document().set({
        "user_id": user_id,
        **fee_data
    })

# Function to reset tournament every 6 months and reward top 100
def reset_tournament_and_reward():
    leaderboard = get_top_users_by_trophies(limit=100)
    reset_pool = calculate_reset_pool()

    for rank, user in enumerate(leaderboard, start=1):
        reset_reward = calculate_reset_payout(rank, reset_pool)
        credit_user_account(user['telegram_id'], reset_reward)

def get_top_users_by_trophies(limit=100):
    # Placeholder: should sort users by trophy count descending
    return get_top_users_by_profit(limit)

def calculate_reset_pool():
    return 3000.00  # Example: sum of 6 months’ worth of 0.25% fees

def calculate_reset_payout(rank, pool):
    if rank == 1:
        return pool * 0.20
    elif rank <= 5:
        return pool * 0.30 / 4
    elif rank <= 20:
        return pool * 0.25 / 15
    else:
        return pool * 0.25 / 80

# Function to save trade history
def log_trade(user_id, symbol, amount, profit, timestamp):
    db.collection("trade_history").add({
        "user_id": user_id,
        "symbol": symbol,
        "amount": amount,
        "profit": profit,
        "timestamp": timestamp
    })

# Analyze emotional patterns (e.g., revenge trades, overtrading)
def analyze_emotional_patterns(user_id):
    trades = get_user_trade_history(user_id)
    revenge_trades = 0
    overtrading = 0

    for i in range(1, len(trades)):
        prev = trades[i - 1]
        current = trades[i]
        if prev["profit"] < 0 and current["amount"] > prev["amount"] * 1.5:
            revenge_trades += 1
        if i >= 5 and all(trade["timestamp"].date() == trades[i]["timestamp"].date() for trade in trades[i-5:i]):
            overtrading += 1

    return {
        "revenge_trades": revenge_trades,
        "overtrading_instances": overtrading
    }

def get_user_trade_history(user_id):
    docs = db.collection("trade_history").where("user_id", "==", user_id).stream()
    return sorted([doc.to_dict() for doc in docs], key=lambda x: x["timestamp"])

# Function for user to select coaching tone
async def set_coaching_tone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tone = " ".join(context.args).strip().lower()
    valid_tones = ["hustler", "monk", "analyst"]

    if tone not in valid_tones:
        await update.message.reply_text(
            "Please choose a valid tone: Hustler, Monk, or Analyst."
        )
        return

    user_id = update.effective_user.id
    db.collection("users").document(str(user_id)).update({
        "tone": tone
    })

    await update.message.reply_text(f"Coaching tone set to: {tone.capitalize()}")

# Function to retrieve user's coaching tone
def get_user_tone(user_id):
    doc = db.collection("users").document(str(user_id)).get()
    if doc.exists:import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, db
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Firebase Initialization
firebase_json = os.getenv("FIREBASE_CREDENTIALS")
if not firebase_json:
    raise ValueError("FIREBASE_CREDENTIALS not set")

cred = credentials.Certificate(json.loads(firebase_json))
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://your-database-url.firebaseio.com/'
})

# Telegram Bot Setup
telegram_bot_token = os.getenv("BOT_TOKEN")
if not telegram_bot_token:
    raise ValueError("BOT_TOKEN not set")

telegram_app = Application.builder().token(telegram_bot_token).build()

# Firebase Database Reference Functions
def get_user_data(telegram_id):
    ref = db.reference(f"users/{telegram_id}")
    return ref.get()

def update_user_data(telegram_id, data):
    ref = db.reference(f"users/{telegram_id}")
    ref.update(data)

# Helper function for adding trade data
def save_trade(telegram_id, trade_data):
    ref = db.reference(f"trades/{telegram_id}")
    ref.push(trade_data)

# Encryption Setup (optional if you're encrypting sensitive data)
SECRET_KEY = os.getenv("SECRET_KEY")
if SECRET_KEY:
    from cryptography.fernet import Fernet
    fernet = Fernet(SECRET_KEY)

# Set up logging for debugging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample Commands to get started
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to Crypto Bot! Type /help for command info.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    /start - Start the bot
    /help - Show this help message
    /register - Register with your API keys
    /balance - View your trading balance
    """
    await update.message.reply_text(help_text)

# Handle user registration and API key linking
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if len(context.args) != 2:
        await update.message.reply_text("Please provide both Binance API key and secret. Usage: /register <API_KEY> <API_SECRET>")
        return

    binance_api_key = context.args[0]
    binance_api_secret = context.args[1]

    # Store the API keys securely in Firebase under the user
    update_user_data(user_id, {
        'binance_api_key': binance_api_key,
        'binance_api_secret': binance_api_secret
    })

    await update.message.reply_text("Your API keys have been registered successfully!")

# Fetch and display balance for registered users
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Example: Use the Binance API to fetch the user's balance
    from binance.client import Client
    client = Client(user_data['binance_api_key'], user_data['binance_api_secret'])
    balance = client.get_account()

    # Show a summary of the balance
    balances = "\n".join([f"{b['asset']}: {b['free']}" for b in balance['balances']])
    await update.message.reply_text(f"Your current balance:\n{balances}")

# Simple trade execution logic (buy/sell)
async def execute_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    if len(context.args) != 3:
        await update.message.reply_text("Usage: /trade <BUY/SELL> <SYMBOL> <AMOUNT>")
        return

    action = context.args[0].upper()
    symbol = context.args[1].upper()
    amount = float(context.args[2])

    if action not in ['BUY', 'SELL']:
        await update.message.reply_text("Invalid action. Please use BUY or SELL.")
        return

    # Initialize Binance client
    from binance.client import Client
    client = Client(user_data['binance_api_key'], user_data['binance_api_secret'])

    try:
        if action == "BUY":
            order = client.order_market_buy(symbol=symbol, quantity=amount)
        elif action == "SELL":
            order = client.order_market_sell(symbol=symbol, quantity=amount)

        # Store the trade data in Firebase
        trade_data = {
            'symbol': symbol,
            'amount': amount,
            'price': order['fills'][0]['price'],
            'action': action,
            'time': str(datetime.now())
        }
        save_trade(user_id, trade_data)

        await update.message.reply_text(f"Trade executed: {action} {amount} {symbol} at {trade_data['price']}")

    except Exception as e:
        await update.message.reply_text(f"Error executing trade: {e}")

# Tournament management logic (example for weekly leaderboard)
async def tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Here we can simulate trading performance and calculate user rank
    # Simulate some kind of performance
    performance_score = 100  # Example score, replace with actual trade logic

    # Add or update performance score in the leaderboard (Firebase)
    leaderboard_ref = db.reference("leaderboard")
    leaderboard = leaderboard_ref.get() or {}
    leaderboard[user_id] = performance_score
    leaderboard_ref.set(leaderboard)

    # Show leaderboard (Top 10 players)
    top_players = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)[:10]
    leaderboard_msg = "\n".join([f"{i+1}. {user_id} - {score}" for i, (user_id, score) in enumerate(top_players)])
    await update.message.reply_text(f"Current Tournament Leaderboard:\n{leaderboard_msg}")

# Example AI-based advice for users
async def edge_ai_advice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Example: Calculate profit/loss based on recent trades
    recent_trades = db.reference(f"trades/{user_id}").get() or {}

    if not recent_trades:
        await update.message.reply_text("No trades found for analysis.")
        return

    total_profit = sum([trade['profit'] for trade in recent_trades.values()])
    advice = "Keep pushing, but consider taking profits after a certain threshold!"

    # AI coaching message
    if total_profit > 0:
        advice = f"You're doing great! Total profit: {total_profit}. {advice}"

    await update.message.reply_text(f"Edge AI Advice: {advice}")

# Handle tournament resets every 6 months and distribute rewards
async def tournament_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get leaderboard and calculate season reset rewards
    leaderboard_ref = db.reference("leaderboard")
    leaderboard = leaderboard_ref.get() or {}

    # Sort leaderboard by performance score (Descending order)
    sorted_leaderboard = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)

    # Allocate rewards (you can adjust this logic based on your prize pool distribution)
    total_tournament_pot = 100000  # Example value, replace with actual prize pool
    reward_per_player = total_tournament_pot // len(sorted_leaderboard)

    # Distribute rewards
    for i, (user_id, score) in enumerate(sorted_leaderboard):
        reward = reward_per_player
        # Optional: Give higher rewards for top performers
        if i < 10:
            reward += 1000  # Extra reward for top 10 players

        # Store the seasonal reset reward data
        user_data = get_user_data(user_id)
        updated_rewards = user_data.get('rewards', 0) + reward
        update_user_data(user_id, {'rewards': updated_rewards})

    # Reset leaderboard for the next season
    leaderboard_ref.set({})
    await update.message.reply_text("Tournament reset complete! Rewards have been distributed.")

# Edge AI emotional coaching
async def edge_ai_emotional_coaching(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Example: Emotional state based on recent trade history
    recent_trades = db.reference(f"trades/{user_id}").get() or {}

    if not recent_trades:
        await update.message.reply_text("No trades found for analysis.")
        return

    losses = sum([trade['loss'] for trade in recent_trades.values()])
    profit = sum([trade['profit'] for trade in recent_trades.values()])

    # Analyze emotional state based on profits and losses
    emotional_state = ""
    if losses > profit:
        emotional_state = "It seems you're feeling the pressure from losses. Take a step back and consider a more conservative strategy."
    elif profit > losses:
        emotional_state = "You're in a good state of profit! Stay disciplined and avoid overtrading."
    else:
        emotional_state = "You're balancing losses and gains. Try to focus on improving your strategy."

    # Send coaching advice based on emotional state
    await update.message.reply_text(f"Edge AI Emotional Coaching: {emotional_state}")

# Track and send alerts when user reaches profit targets
async def track_profit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Example: Track user balance change over time (Profit/Loss)
    initial_balance = user_data.get('initial_balance', 1000)  # Assuming the initial balance is set during registration
    current_balance = user_data.get('current_balance', initial_balance)

    profit = current_balance - initial_balance
    profit_target = 100  # Example target, can be dynamic or set by user

    # Send alert if the user reaches their profit target
    if profit >= profit_target:
        await update.message.reply_text(f"Congratulations! You've reached your profit target of {profit_target} ZAR! Total profit: {profit} ZAR")

    # Update current balance in Firebase
    update_user_data(user_id, {'current_balance': current_balance})

# Display user's trade history and performance
async def trade_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Fetch trade data
    trades_ref = db.reference(f"trades/{user_id}")
    trades = trades_ref.get()

    if not trades:
        await update.message.reply_text("No trades found.")
        return

    # Display trade history
    trade_history_message = "Your Trade History:\n"
    for trade_id, trade_data in trades.items():
        trade_history_message += f"ID: {trade_id}\n"
        trade_history_message += f"Symbol: {trade_data['symbol']}, Amount: {trade_data['amount']}, Price: {trade_data['price']}\n"
        trade_history_message += f"Action: {trade_data['action']}, Profit: {trade_data['profit']}, Loss: {trade_data['loss']}\n\n"

    await update.message.reply_text(trade_history_message)

# Monthly leaderboard reset and prize distribution
async def monthly_leaderboard_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leaderboard_ref = db.reference("leaderboard")
    leaderboard = leaderboard_ref.get() or {}

    # Sort leaderboard by performance score (Descending order)
    sorted_leaderboard = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)

    # Allocate rewards for the top players
    total_monthly_prize_pool = 50000  # Example monthly prize pool value
    monthly_reward_per_player = total_monthly_prize_pool // len(sorted_leaderboard)

    for i, (user_id, score) in enumerate(sorted_leaderboard):
        reward = monthly_reward_per_player
        # Optional: Extra rewards for top 5 players
        if i < 5:
            reward += 500

        # Store rewards in user's data
        user_data = get_user_data(user_id)
        updated_rewards = user_data.get('rewards', 0) + reward
        update_user_data(user_id, {'rewards': updated_rewards})

    # Reset leaderboard for next month
    leaderboard_ref.set({})
    await update.message.reply_text("Monthly leaderboard reset complete! Rewards distributed to top players.")

# Send alerts when a trade hits stop-loss or take-profit points
async def trade_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Fetch the user's trade status
    trade_ref = db.reference(f"trades/{user_id}")
    trades = trade_ref.get()

    if not trades:
        await update.message.reply_text("No trades in progress.")
        return

    # Check each trade's status
    for trade_id, trade_data in trades.items():
        current_price = get_current_price(trade_data['symbol'])  # Example function to get live price
        stop_loss = trade_data.get('stop_loss')
        take_profit = trade_data.get('take_profit')

        # Check if price hits stop-loss or take-profit
        if stop_loss and current_price <= stop_loss:
            await update.message.reply_text(f"Stop-Loss Triggered: Trade ID {trade_id} has hit your stop-loss!")
            # Optional: Automatically close the trade if needed
            close_trade(user_id, trade_id)

        if take_profit and current_price >= take_profit:
            await update.message.reply_text(f"Take-Profit Triggered: Trade ID {trade_id} has hit your take-profit!")
            # Optional: Automatically close the trade if needed
            close_trade(user_id, trade_id)

# Function to get the current price of a trading pair
def get_current_price(symbol):
    # Placeholder function for live price fetching from Binance or Luno
    # You should implement Binance API or Luno API calls to get real-time price data
    # Example for Binance API:
    # response = binance_client.get_symbol_ticker(symbol=symbol)
    # return response['price']

    # Simulating a price fetch for now
    return 10000  # Example price for a symbol

# Function to allow users to set custom alerts for price changes
async def set_price_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Get price alert settings from the user
    try:
        target_price = float(context.args[0])  # Expecting the target price in args
        symbol = context.args[1]  # Expecting the symbol like 'BTCUSDT'
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /set_price_alert <price> <symbol>")
        return

    # Store the alert in the database
    price_alert_ref = db.reference(f"price_alerts/{user_id}")
    price_alert_ref.set({'target_price': target_price, 'symbol': symbol})

    await update.message.reply_text(f"Price alert set! You'll be notified when {symbol} reaches {target_price}.")

# Function to automatically execute trades based on a given strategy
async def auto_trade_execution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Example: Check user’s balance and decide whether to trade
    balance = get_user_balance(user_id)  # Implement this to fetch user balance from Binance API
    risk_percentage = 0.02  # Risk 2% of the balance for each trade

    trade_amount = balance * risk_percentage
    symbol = "BTCUSDT"  # Example trading pair

    # Example of auto-buy logic (simplified)
    if balance >= trade_amount:
        order = execute_trade(symbol, trade_amount)
        await update.message.reply_text(f"Executing auto-trade: {order}")
    else:
        await update.message.reply_text("Insufficient balance for trade.")
    
def execute_trade(symbol, amount):
    # Placeholder function to execute trade
    # You should implement Binance API calls to place the order
    # Example: binance_client.order_market_buy(symbol=symbol, quantity=amount)
    return f"Order placed for {amount} of {symbol}"

# Function to analyze the user's trading behavior
async def behavioral_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Analyze recent trade history for patterns
    trades_ref = db.reference(f"trades/{user_id}")
    trades = trades_ref.get()

    if not trades:
        await update.message.reply_text("No trades found for analysis.")
        return

    # Example: Analyze if the user is overtrading
    trade_count = len(trades)
    overtrading_threshold = 10  # Example threshold

    if trade_count > overtrading_threshold:
        await update.message.reply_text("Warning: You are trading too frequently! Consider reviewing your strategy.")
    else:
        await update.message.reply_text("Your trade frequency looks balanced. Keep it up!")

# Update leaderboard dynamically based on user performance
async def update_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Calculate user performance (profit, trade success rate, etc.)
    performance_score = calculate_performance_score(user_id)  # You need to define this based on your criteria

    # Update leaderboard
    leaderboard_ref = db.reference("leaderboard")
    leaderboard = leaderboard_ref.get() or {}

    # Add or update user performance in the leaderboard
    leaderboard[user_id] = performance_score
    leaderboard_ref.set(leaderboard)

    await update.message.reply_text(f"Your performance has been updated! Current leaderboard score: {performance_score}")

def calculate_performance_score(user_id):
    # Placeholder function for calculating performance score
    # You should implement logic to calculate the score based on user performance
    return 100  # Example score

# Enable trade simulation for users to test strategies without real money
async def trade_simulation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Start a simulation mode (user will not be trading with real funds)
    simulation_balance = 10000  # Example starting balance for simulation
    user_data['simulation_mode'] = True  # Flag to indicate the user is in simulation mode
    update_user_data(user_id, user_data)

    await update.message.reply_text("You are now in trade simulation mode! You can test your strategies without real money.")

# Simulate a trade execution in simulation mode
async def simulate_trade_execution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if user_data.get('simulation_mode', False):
        # Execute trade using the simulated balance
        trade_amount = 1000  # Example amount to trade
        simulation_balance = user_data.get('simulation_balance', 10000)

        if simulation_balance >= trade_amount:
            new_balance = simulation_balance - trade_amount
            user_data['simulation_balance'] = new_balance
            update_user_data(user_id, user_data)

            await update.message.reply_text(f"Simulated trade executed! New simulated balance: {new_balance}")
        else:
            await update.message.reply_text("Insufficient funds in simulation mode.")
    else:
        await update.message.reply_text("You need to enter simulation mode first using /trade_simulation.")

# Function to display portfolio balance and individual asset performance
async def show_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Fetch user's portfolio data from Binance API (or simulate it for now)
    portfolio_data = get_user_portfolio(user_data['binance_api_key'])

    # Display user's portfolio performance
    portfolio_message = "Your Portfolio:\n"
    for asset, data in portfolio_data.items():
        portfolio_message += f"{asset}: {data['quantity']} - Value: {data['value']} USD\n"

    # Display total portfolio value and profit/loss
    total_value = sum([data['value'] for data in portfolio_data.values()])
    profit_loss = total_value - user_data['initial_balance']
    portfolio_message += f"Total Value: {total_value} USD\n"
    portfolio_message += f"Profit/Loss: {profit_loss} USD\n"

    await update.message.reply_text(portfolio_message)

def get_user_portfolio(api_key):
    # Placeholder function to fetch portfolio data from Binance or other exchanges
    # In a real implementation, use Binance API to fetch user's portfolio
    return {
        'BTC': {'quantity': 0.5, 'value': 25000},
        'ETH': {'quantity': 10, 'value': 20000},
        'USDT': {'quantity': 1000, 'value': 1000}
    }

# Function to allow users to define custom trading strategies
async def set_custom_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Expecting strategy parameters from the user
    try:
        strategy_type = context.args[0]  # Example: 'MACD' or 'RSI'
        entry_condition = context.args[1]  # Example: 'crosses above 50'
        exit_condition = context.args[2]  # Example: 'crosses below 50'
    except IndexError:
        await update.message.reply_text("Usage: /set_strategy <strategy_type> <entry_condition> <exit_condition>")
        return

    # Save the strategy to the database
    strategy_ref = db.reference(f"strategies/{user_id}")
    strategy_ref.set({'strategy_type': strategy_type, 'entry_condition': entry_condition, 'exit_condition': exit_condition})

    await update.message.reply_text(f"Custom strategy set! Type: {strategy_type}, Entry: {entry_condition}, Exit: {exit_condition}")

# Function to evaluate custom strategy conditions during each trade
def evaluate_strategy(symbol, user_data):
    strategy_ref = db.reference(f"strategies/{user_data['telegram_id']}")
    strategy = strategy_ref.get()

    if not strategy:
        return False  # No strategy set

    # Example: Evaluate entry condition based on market data (e.g., MACD, RSI)
    entry_condition = strategy.get('entry_condition')
    if entry_condition == 'crosses above 50':  # Placeholder condition for testing
        current_indicator_value = get_current_indicator_value(symbol)  # Placeholder for MACD or RSI value
        if current_indicator_value > 50:
            return True  # Entry condition met

    return False

def get_current_indicator_value(symbol):
    # Placeholder function for fetching market indicator value (e.g., MACD, RSI)
    return 60  # Example value

# Function to execute trades based on custom strategy
async def execute_strategy_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Get the custom strategy for the user
    strategy_ref = db.reference(f"strategies/{user_id}")
    strategy = strategy_ref.get()

    if not strategy:
        await update.message.reply_text("You don't have a custom strategy set.")
        return

    symbol = "BTCUSDT"  # Example symbol
    trade_amount = 1000  # Example trade amount

    # Check if the strategy's entry condition is met
    if evaluate_strategy(symbol, user_data):
        order = execute_trade(symbol, trade_amount)
        await update.message.reply_text(f"Strategy triggered: {order}")
    else:
        await update.message.reply_text("Strategy conditions not met. No trade executed.")

# Function to track and close trades
async def monitor_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    trade_ref = db.reference(f"trades/{user_id}")
    trades = trade_ref.get()

    if not trades:
        await update.message.reply_text("No trades in progress.")
        return

    # Check for open trades and close them if certain conditions are met
    for trade_id, trade_data in trades.items():
        current_price = get_current_price(trade_data['symbol'])

        if current_price >= trade_data['take_profit']:
            close_trade(user_id, trade_id)
            await update.message.reply_text(f"Take-profit reached. Trade {trade_id} closed.")
        elif current_price <= trade_data['stop_loss']:
            close_trade(user_id, trade_id)
            await update.message.reply_text(f"Stop-loss reached. Trade {trade_id} closed.")

def close_trade(user_id, trade_id):
    # Placeholder function to close the trade
    # You should implement Binance API call to cancel or close the trade
    return f"Trade {trade_id} closed for user {user_id}"

# Function to display advanced user analytics
async def show_user_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Fetch user’s trade history and performance
    trade_history = get_user_trade_history(user_id)

    if not trade_history:
        await update.message.reply_text("No trade history found.")
        return

    # Calculate total profit/loss and win rate
    total_profit = sum([trade['profit'] for trade in trade_history])
    total_trades = len(trade_history)
    win_rate = sum([1 for trade in trade_history if trade['profit'] > 0]) / total_trades * 100

    analytics_message = f"User Analytics:\nTotal Profit/Loss: {total_profit} USD\n"
    analytics_message += f"Total Trades: {total_trades}\nWin Rate: {win_rate}%"

    await update.message.reply_text(analytics_message)

def get_user_trade_history(user_id):
    # Placeholder function to fetch trade history from the database
    return [
        {'trade_id': 1, 'profit': 500},
        {'trade_id': 2, 'profit': -200},
        {'trade_id': 3, 'profit': 300}
    ]

# Function to set stop-loss and take-profit orders automatically
async def set_auto_stop_loss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    try:
        stop_loss_price = float(context.args[0])
        take_profit_price = float(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /set_auto_stop_loss <stop_loss_price> <take_profit_price>")
        return

    # Save the stop-loss and take-profit to the database for later use
    stop_loss_ref = db.reference(f"stop_loss/{user_id}")
    stop_loss_ref.set({'stop_loss': stop_loss_price, 'take_profit': take_profit_price})

    await update.message.reply_text(f"Stop-loss and take-profit set! Stop-Loss: {stop_loss_price}, Take-Profit: {take_profit_price}")

# Function to set up real-time price monitoring and alerts for a specific asset
async def set_price_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    try:
        symbol = context.args[0]  # Example: 'BTCUSDT'
        alert_price = float(context.args[1])  # Price to trigger the alert
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /set_price_alert <symbol> <alert_price>")
        return

    # Save the price alert to the database
    alert_ref = db.reference(f"price_alerts/{user_id}")
    alert_ref.set({'symbol': symbol, 'alert_price': alert_price})

    await update.message.reply_text(f"Price alert set for {symbol} at {alert_price} USD.")

# Function to monitor the prices and send alerts
def monitor_price_alerts():
    # Placeholder function for real-time price monitoring
    # Fetch all price alerts from the database
    price_alerts_ref = db.reference("price_alerts")
    price_alerts = price_alerts_ref.get()

    if not price_alerts:
        return

    # Check if any alerts are triggered
    for user_id, alerts in price_alerts.items():
        for alert in alerts:
            current_price = get_current_price(alert['symbol'])
            if current_price >= alert['alert_price']:
                send_price_alert(user_id, alert['symbol'], current_price)

def get_current_price(symbol):
    # Placeholder function to fetch the current price of an asset
    return 60000  # Example price, this should be fetched from Binance or other exchange API

def send_price_alert(user_id, symbol, current_price):
    # Function to send a price alert to the user
    user_telegram_id = get_user_telegram_id(user_id)
    message = f"Price Alert! {symbol} has reached {current_price} USD."
    send_telegram_message(user_telegram_id, message)

def send_telegram_message(user_telegram_id, message):
    # Send the message to the user's Telegram account
    context.bot.send_message(chat_id=user_telegram_id, text=message)

def get_user_telegram_id(user_id):
    # Function to get the user's Telegram ID from the database
    return db.reference(f"users/{user_id}/telegram_id").get()

# Function to review trade history for performance analysis
async def review_trade_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Fetch trade history from the database
    trade_history_ref = db.reference(f"trades/{user_id}")
    trade_history = trade_history_ref.get()

    if not trade_history:
        await update.message.reply_text("You have no trade history.")
        return

    # Summarize the trade history
    trade_summary = "Your Trade History:\n"
    total_profit = 0
    win_count = 0
    loss_count = 0

    for trade in trade_history:
        profit = trade.get('profit', 0)
        total_profit += profit
        if profit > 0:
            win_count += 1
        elif profit < 0:
            loss_count += 1

        trade_summary += f"Trade {trade['trade_id']}: {profit} USD\n"

    # Provide a detailed summary
    trade_summary += f"\nTotal Profit: {total_profit} USD\n"
    trade_summary += f"Win Rate: {win_count / len(trade_history) * 100}%\n"
    trade_summary += f"Loss Rate: {loss_count / len(trade_history) * 100}%\n"

    await update.message.reply_text(trade_summary)

# Function to track user progress and achievements
async def track_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Track achievements based on trading milestones
    achievements = get_user_achievements(user_id)

    achievements_message = "Your Achievements:\n"
    for achievement in achievements:
        achievements_message += f"{achievement['name']}: {achievement['status']}\n"

    await update.message.reply_text(achievements_message)

def get_user_achievements(user_id):
    # Placeholder function to fetch user achievements
    return [
        {'name': 'First Trade', 'status': 'Completed'},
        {'name': '1000 USD Profit', 'status': 'In Progress'},
        {'name': 'Risk-Free Trader', 'status': 'Unlocked'}
    ]

# Function to track and display bot performance metrics
async def show_bot_performance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Bot performance metrics to be tracked (e.g., success rate, trades executed, total profits)
    performance_data = get_bot_performance()

    performance_message = "Bot Performance Metrics:\n"
    performance_message += f"Total Trades Executed: {performance_data['total_trades']}\n"
    performance_message += f"Successful Trades: {performance_data['successful_trades']}\n"
    performance_message += f"Success Rate: {performance_data['success_rate']}%\n"
    performance_message += f"Total Profit: {performance_data['total_profit']} USD\n"

    await update.message.reply_text(performance_message)

def get_bot_performance():
    # Placeholder function for fetching bot performance data
    return {
        'total_trades': 150,
        'successful_trades': 120,
        'success_rate': 80,
        'total_profit': 5000
    }

# Function to schedule trades at specific times
async def schedule_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    try:
        trade_time = context.args[0]  # Format: 'HH:MM'
        symbol = context.args[1]  # Symbol to trade, e.g., 'BTCUSDT'
        amount = float(context.args[2])  # Amount to trade
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /schedule_trade <HH:MM> <symbol> <amount>")
        return

    # Convert the time to seconds since midnight for scheduling
    scheduled_time = convert_to_seconds(trade_time)
    scheduled_trade_ref = db.reference(f"scheduled_trades/{user_id}")
    scheduled_trade_ref.set({'time': scheduled_time, 'symbol': symbol, 'amount': amount})

    await update.message.reply_text(f"Trade scheduled at {trade_time} for {amount} {symbol}.")

def convert_to_seconds(time_str):
    # Convert 'HH:MM' to seconds since midnight
    hours, minutes = map(int, time_str.split(":"))
    return hours * 3600 + minutes * 60

# Function to execute scheduled trades at the correct time
def execute_scheduled_trades():
    # Placeholder function to execute scheduled trades at the right time
    scheduled_trades_ref = db.reference("scheduled_trades")
    scheduled_trades = scheduled_trades_ref.get()

    for user_id, trades in scheduled_trades.items():
        for trade in trades:
            if check_if_trade_time(trade['time']):
                execute_trade(trade['symbol'], trade['amount'])

def check_if_trade_time(scheduled_time):
    # Placeholder check function for trade timing
    current_time = time.time()
    return current_time >= scheduled_time

# Function to provide feedback on trade execution
async def trade_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    trade_id = context.args[0]  # Trade ID to fetch feedback for
    trade_feedback = get_trade_feedback(user_id, trade_id)

    if not trade_feedback:
        await update.message.reply_text("No feedback available for this trade.")
        return

    await update.message.reply_text(f"Trade Feedback for Trade {trade_id}: {trade_feedback}")

def get_trade_feedback(user_id, trade_id):
    # Placeholder function to fetch trade feedback
    return "Trade executed successfully. Profit: 150 USD."

# Function to calculate trade risk based on the user's balance and chosen trade parameters
def calculate_trade_risk(user_balance, trade_amount):
    # Placeholder for risk management logic
    risk_factor = 0.02  # Example: 2% of the balance can be risked per trade
    max_risk = user_balance * risk_factor

    if trade_amount > max_risk:
        return False, max_risk
    return True, max_risk

# Function to execute a trade with risk management checks
async def execute_trade_with_risk_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    try:
        symbol = context.args[0]  # Symbol to trade (e.g., 'BTCUSDT')
        amount = float(context.args[1])  # Amount to trade
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /execute_trade <symbol> <amount>")
        return

    # Fetch the user's balance
    user_balance = get_user_balance(user_id)

    # Risk check before executing the trade
    is_safe, max_risk = calculate_trade_risk(user_balance, amount)
    if not is_safe:
        await update.message.reply_text(f"Risk too high! You can only risk up to {max_risk} USD per trade.")
        return

    # Proceed with the trade execution
    trade_successful = execute_trade(symbol, amount)

    if trade_successful:
        await update.message.reply_text(f"Trade executed successfully for {amount} {symbol}.")
    else:
        await update.message.reply_text("Trade execution failed. Please try again.")

def get_user_balance(user_id):
    # Placeholder function to fetch user balance from the exchange
    return 1000  # Example balance in USD

def execute_trade(symbol, amount):
    # Placeholder function to execute the trade on the exchange
    # This should interface with Binance API or similar exchange APIs
    return True  # Return True if the trade was successful

# Function to analyze the performance of a given strategy
def analyze_strategy_performance(strategy_data):
    # Example analysis of strategy performance (win rate, average profit per trade, etc.)
    total_trades = len(strategy_data)
    successful_trades = sum(1 for trade in strategy_data if trade['profit'] > 0)
    total_profit = sum(trade['profit'] for trade in strategy_data)

    win_rate = (successful_trades / total_trades) * 100 if total_trades > 0 else 0
    average_profit = total_profit / total_trades if total_trades > 0 else 0

    return {
        'win_rate': win_rate,
        'average_profit': average_profit,
        'total_trades': total_trades,
        'total_profit': total_profit
    }

# Function to suggest strategy improvements based on performance
async def suggest_strategy_improvements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Fetch strategy performance data from the database
    strategy_data = get_strategy_performance(user_id)

    if not strategy_data:
        await update.message.reply_text("No strategy performance data available.")
        return

    performance_metrics = analyze_strategy_performance(strategy_data)

    # Provide the user with strategy feedback
    performance_feedback = f"Strategy Performance:\n"
    performance_feedback += f"Win Rate: {performance_metrics['win_rate']}%\n"
    performance_feedback += f"Average Profit: {performance_metrics['average_profit']} USD\n"
    performance_feedback += f"Total Trades: {performance_metrics['total_trades']}\n"
    performance_feedback += f"Total Profit: {performance_metrics['total_profit']} USD\n"

    # Suggest improvements if necessary
    if performance_metrics['win_rate'] < 60:
        performance_feedback += "\nYour strategy's win rate is low. Consider adjusting your risk management or entry/exit points."

    await update.message.reply_text(performance_feedback)

def get_strategy_performance(user_id):
    # Placeholder function to fetch the user's strategy performance data from the database
    return [
        {'profit': 50}, {'profit': -10}, {'profit': 100}, {'profit': 20}, {'profit': -5}
    ]

# Function to send personalized trade suggestions and market alerts
async def send_trade_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    # Example trade suggestions based on market trends (should integrate with market data)
    trade_suggestions = [
        {"symbol": "BTCUSDT", "suggestion": "Buy", "target_price": 65000},
        {"symbol": "ETHUSDT", "suggestion": "Sell", "target_price": 4000},
    ]

    suggestion_message = "Trade Suggestions:\n"
    for suggestion in trade_suggestions:
        suggestion_message += f"{suggestion['symbol']}: {suggestion['suggestion']} (Target: {suggestion['target_price']} USD)\n"

    await update.message.reply_text(suggestion_message)

# Function to send periodic market updates to users
def send_periodic_market_update():
    # Placeholder function to send market updates to users periodically
    market_update = "Market Update: BTC has increased by 5% today. Consider reviewing your positions."
    
    # Fetch all users from the database and send the update
    all_users = get_all_users()
    for user in all_users:
        send_telegram_message(user['telegram_id'], market_update)

def get_all_users():
    # Placeholder function to fetch all users from the database
    return [
        {"telegram_id": "123456789"},
        {"telegram_id": "987654321"}
    ]

# Function to generate trade entry signals based on simple moving average (SMA)
def generate_trade_signal(symbol):
    # Example using SMA as a strategy for generating trade signals
    prices = get_historical_prices(symbol)
    short_sma = sum(prices[-10:]) / 10  # Last 10 prices
    long_sma = sum(prices[-50:]) / 50   # Last 50 prices

    if short_sma > long_sma:
        return "Buy"
    elif short_sma < long_sma:
        return "Sell"
    return "Hold"

def get_historical_prices(symbol):
    # Placeholder for fetching historical prices from the exchange
    return [60000, 60500, 61000, 61500, 62000, 62500, 63000, 63500, 64000, 64500]  # Example price data

# Function to notify users when a signal is generated
async def send_trade_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data or 'binance_api_key' not in user_data:
        await update.message.reply_text("You need to register your API keys first using /register.")
        return

    try:
        symbol = context.args[0]  # Symbol to generate signal for (e.g., 'BTCUSDT')
    except IndexError:
        await update.message.reply_text("Usage: /send_trade_signal <symbol>")
        return

    # Generate the trade signal
    signal = generate_trade_signal(symbol)
    await update.message.reply_text(f"Trade Signal for {symbol}: {signal}")

# Function to handle errors gracefully and provide user-friendly messages
async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Try to execute the command
        await execute_trade_with_risk_management(update, context)
    except Exception as e:
        # Log the error and send a user-friendly message
        logging.error(f"Error occurred: {e}")
        await update.message.reply_text("An error occurred while processing your request. Please try again later.")

# Function to automatically restart the bot in case of failures (resilience)
def restart_bot():
    # Placeholder function to restart the bot (e.g., if running on a server)
    logging.info("Bot is restarting due to a failure...")
    os.execv(sys.executable, ['python'] + sys.argv)

# Function to fetch leaderboard standings
async def get_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = get_top_users_by_profit()
    leaderboard_text = "Top Traders Leaderboard:\n\n"

    for idx, user in enumerate(top_users, start=1):
        leaderboard_text += f"{idx}. {user['username']} - Profit: ${user['total_profit']:.2f}, Trophies: {user['trophies']}\n"

    await update.message.reply_text(leaderboard_text)

def get_top_users_by_profit(limit=10):
    # Placeholder: Fetch top users based on total profit and trophies
    return [
        {"username": "trader1", "total_profit": 2500.50, "trophies": 3},
        {"username": "trader2", "total_profit": 2300.00, "trophies": 2},
        {"username": "trader3", "total_profit": 2100.75, "trophies": 1},
    ][:limit]

# Function to award trophies based on periodic performance
def award_trophies():
    users = get_all_users()
    for user in users:
        user_profit = calculate_user_profit(user['telegram_id'])
        if user_profit > 1000:  # Example threshold
            increment_user_trophies(user['telegram_id'])

def calculate_user_profit(user_id):
    # Placeholder for calculating total profit from trades
    return 1500  # Example

def increment_user_trophies(user_id):
    # Add 1 trophy to the user's Firebase record
    user_ref = db.collection("users").document(str(user_id))
    user_doc = user_ref.get()
    if user_doc.exists:
        current_trophies = user_doc.to_dict().get("trophies", 0)
        user_ref.update({"trophies": current_trophies + 1})

# Function to simulate a tournament payout to top 100 players
def distribute_tournament_rewards():
    prize_pool = calculate_total_prize_pool()
    top_players = get_top_users_by_profit(limit=100)

    for rank, user in enumerate(top_players, start=1):
        payout = calculate_tiered_payout(rank, prize_pool)
        credit_user_account(user['telegram_id'], payout)

def calculate_total_prize_pool():
    # Example: 1% of all user profits go into the prize pool
    return 5000.00  # Placeholder amount

def calculate_tiered_payout(rank, total_pool):
    if rank == 1:
        return total_pool * 0.25
    elif rank <= 5:
        return total_pool * 0.15 / 4
    elif rank <= 20:
        return total_pool * 0.30 / 15
    else:
        return total_pool * 0.30 / 80

def credit_user_account(user_id, amount):
    user_ref = db.collection("users").document(str(user_id))
    user_doc = user_ref.get()
    if user_doc.exists:
        current_balance = user_doc.to_dict().get("reward_balance", 0)
        user_ref.update({"reward_balance": current_balance + amount})

# Function to deduct 1.25% tournament fee from profitable trades
def deduct_tournament_fee(user_id, profit):
    if profit <= 0:
        return

    tournament_cut = profit * 0.0125
    app_fee = profit * 0.0025
    pool_fee = profit * 0.007
    reset_fee = profit * 0.003

    record_fee_distribution(user_id, app_fee, pool_fee, reset_fee)

def record_fee_distribution(user_id, app_fee, pool_fee, reset_fee):
    fee_data = {
        "app_fee": app_fee,
        "pool_fee": pool_fee,
        "reset_fee": reset_fee,
        "timestamp": datetime.utcnow()
    }
    db.collection("fees").document().set({
        "user_id": user_id,
        **fee_data
    })

# Function to reset tournament every 6 months and reward top 100
def reset_tournament_and_reward():
    leaderboard = get_top_users_by_trophies(limit=100)
    reset_pool = calculate_reset_pool()

    for rank, user in enumerate(leaderboard, start=1):
        reset_reward = calculate_reset_payout(rank, reset_pool)
        credit_user_account(user['telegram_id'], reset_reward)

def get_top_users_by_trophies(limit=100):
    # Placeholder: should sort users by trophy count descending
    return get_top_users_by_profit(limit)

def calculate_reset_pool():
    return 3000.00  # Example: sum of 6 months’ worth of 0.25% fees

def calculate_reset_payout(rank, pool):
    if rank == 1:
        return pool * 0.20
    elif rank <= 5:
        return pool * 0.30 / 4
    elif rank <= 20:
        return pool * 0.25 / 15
    else:
        return pool * 0.25 / 80

# Function to save trade history
def log_trade(user_id, symbol, amount, profit, timestamp):
    db.collection("trade_history").add({
        "user_id": user_id,
        "symbol": symbol,
        "amount": amount,
        "profit": profit,
        "timestamp": timestamp
    })

# Analyze emotional patterns (e.g., revenge trades, overtrading)
def analyze_emotional_patterns(user_id):
    trades = get_user_trade_history(user_id)
    revenge_trades = 0
    overtrading = 0

    for i in range(1, len(trades)):
        prev = trades[i - 1]
        current = trades[i]
        if prev["profit"] < 0 and current["amount"] > prev["amount"] * 1.5:
            revenge_trades += 1
        if i >= 5 and all(trade["timestamp"].date() == trades[i]["timestamp"].date() for trade in trades[i-5:i]):
            overtrading += 1

    return {
        "revenge_trades": revenge_trades,
        "overtrading_instances": overtrading
    }

def get_user_trade_history(user_id):
    docs = db.collection("trade_history").where("user_id", "==", user_id).stream()
    return sorted([doc.to_dict() for doc in docs], key=lambda x: x["timestamp"])

# Function for user to select coaching tone
async def set_coaching_tone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tone = " ".join(context.args).strip().lower()
    valid_tones = ["hustler", "monk", "analyst"]

    if tone not in valid_tones:
        await update.message.reply_text(
            "Please choose a valid tone: Hustler, Monk, or Analyst."
        )
        return

    user_id = update.effective_user.id
    db.collection("users").document(str(user_id)).update({
        "tone": tone
    })

    await update.message.reply_text(f"Coaching tone set to: {tone.capitalize()}")

# Function to retrieve user's coaching tone
def get_user_tone(user_id):
    doc = db.collection("users").document(str(user_id)).get()
    if doc.exists:
        return doc.to_dict().get("tone", "analyst")
    return "analyst"

# Generate personalized coaching message based on selected tone
def generate_coaching_message(tone, context_data):
    if tone == "hustler":
        return f"Let’s go! You crushed it with a profit of ${context_data['profit']:.2f}. Keep the pressure on."
    elif tone == "monk":
        return f"Calm progress. A profit of ${context_data['profit']:.2f} today. Keep practicing discipline."
    elif tone == "analyst":
        return f"Profit logged: ${context_data['profit']:.2f}. Stats are improving. Analyzing next moves..."
    else:
        return f"Profit of ${context_data['profit']:.2f} noted."

# Example coaching usage after trade log
def notify_user_with_coaching(user_id, profit):
    tone = get_user_tone(user_id)
    context_data = {"profit": profit}
    message = generate_coaching_message(tone, context_data)
    send_telegram_message(user_id, message)

# Telegram message sender
def send_telegram_message(user_id, message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": user_id,
        "text": message
    }
    requests.post(url, json=payload)

# Placeholder for WhatsApp via Twilio or third-party webhook
def send_whatsapp_alert(phone_number, message):
    # Needs Twilio setup with auth token and from number
    twilio_url = "https://api.twilio.com/..."
    headers = {
        "Authorization": f"Basic {TWILIO_AUTH_ENCODED}"
    }
    data = {
        "To": f"whatsapp:{phone_number}",
        "From": "whatsapp:+YOUR_TWILIO_NUMBER",
        "Body": message
    }
    requests.post(twilio_url, data=data, headers=headers)

# Update user alert preference
async def set_alert_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    method = " ".join(context.args).strip().lower()
    valid_methods = ["telegram", "whatsapp"]

    if method not in valid_methods:
        await update.message.reply_text("Choose either 'telegram' or 'whatsapp'.")
        return

    user_id = update.effective_user.id
    db.collection("users").document(str(user_id)).update({
        "alert_method": method
    })

    await update.message.reply_text(f"Alert method set to: {method.capitalize()}")

# Send trade alert based on user setting
def notify_trade_signal(user_id, message):
    doc = db.collection("users").document(str(user_id)).get()
    if doc.exists:
        user = doc.to_dict()
        method = user.get("alert_method", "telegram")
        if method == "telegram":
            send_telegram_message(user_id, message)
        elif method == "whatsapp" and "phone" in user:
            send_whatsapp_alert(user["phone"], message)

# Function to detect risky trading patterns
def detect_risky_trade_behavior(user_id, recent_trade):
    history = get_user_trade_history(user_id)
    losses = [t for t in history[-3:] if t["profit"] < 0]

    if len(losses) >= 3:
        return "Warning: You've taken 3 losses in a row. Consider pausing or adjusting your strategy."

    if recent_trade["amount"] > 3 * avg_trade_amount(history):
        return "Caution: This trade is much larger than your average size. Confirm you want to proceed."

    return None

def avg_trade_amount(history):
    if not history:
        return 1
    return sum(t["amount"] for t in history) / len(history)

# Called when user sends /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_ref = db.collection("users").document(str(user.id))

    if not user_ref.get().exists:
        user_ref.set({
            "telegram_id": user.id,
            "username": user.username or "",
            "api_keys": {},
            "tone": "analyst",
            "alert_method": "telegram",
            "created_at": datetime.utcnow().isoformat()
        })
        await update.message.reply_text(
            f"Welcome, {user.first_name}! Your profile has been created. Send /help to begin."
        )
    else:
        await update.message.reply_text("Welcome back! Type /menu to explore options.")

async def view_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    doc = db.collection("users").document(str(user_id)).get()

    if not doc.exists:
        await update.message.reply_text("User not found. Try /start.")
        return

    user = doc.to_dict()
    settings_text = (
        f"**Your Settings:**\n"
        f"- Coaching Tone: {user.get('tone', 'Not set')}\n"
        f"- Alert Method: {user.get('alert_method', 'telegram')}\n"
        f"- Registered Username: @{user.get('username', 'N/A')}\n"
    )
    await update.message.reply_text(settings_text, parse_mode="Markdown")

async def update_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_username = " ".join(context.args).strip()
    if not new_username:
        await update.message.reply_text("Send /setusername <your_username>")
        return

    user_id = update.effective_user.id
    db.collection("users").document(str(user_id)).update({
        "username": new_username
    })

    await update.message.reply_text(f"Username updated to @{new_username}")

# Register all handlers in app.py or main.py
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("settone", set_coaching_tone))
app.add_handler(CommandHandler("setalert", set_alert_method))
app.add_handler(CommandHandler("settings", view_settings))
app.add_handler(CommandHandler("setusername", update_username))
app.add_handler(CommandHandler("linkbinance", link_binance_api))
app.add_handler(CommandHandler("linkluno", link_luno_api))
app.add_handler(CommandHandler("logtrade", log_trade_command))
app.add_handler(CommandHandler("tradehistory", show_trade_history))

async def show_trade_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    trades = db.collection("trades").where("user_id", "==", str(user_id)).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(5).stream()

    history = []
    for trade in trades:
        t = trade.to_dict()
        summary = f"{t['timestamp'][:16]} | {t['symbol']} | PnL: ${t['profit']:.2f}"
        history.append(summary)

    if not history:
        await update.message.reply_text("No trades found yet.")
    else:
        await update.message.reply_text("\n".join(history))

# Simple mood-based encouragement
def emotional_nudge(user_id, recent_profit):
    tone = get_user_tone(user_id)
    if recent_profit < 0:
        if tone == "monk":
            return "Losses are part of the path. Breathe. Stick to your plan."
        elif tone == "hustler":
            return "Bounce back mode activated! Regroup and fire again."
        elif tone == "analyst":
            return "Negative trade logged. Let's review data and adjust."
    else:
        return None

def calculate_all_deductions(profit, tournament_enabled=True):
    # Your fee: 0.50% on all trades
    # Tournament total: 1.25% (0.25% to you, 1% to players)
    total_fee = 0.005  # base fee (0.50%)
    
    tournament_fee = 0.0125 if tournament_enabled else 0  # 1.25%
    total_fee += tournament_fee

    return profit * total_fee

def split_tournament_fees(total_tournament_fee):
    return {
        "your_cut_from_tournament": total_tournament_fee * 0.20,       # 0.25% = 20% of 1.25%
        "player_tournament_pool": total_tournament_fee * 0.80          # 1% = 80% of 1.25%
    }

def breakdown_player_tournament_pool(player_pool_amount):
    return {
        "daily_weekly_pool": player_pool_amount * 0.70,  # 70% of 1%
        "trophy_reset_pool": player_pool_amount * 0.30   # 30% of 1%
    }

def log_fee_distribution(user_id, trade_id, profit, total_fee):
    tournament_split = split_tournament_fees(total_fee * (1.25 / (0.5 + 1.25)))  # Isolate 1.25
    player_split = breakdown_player_tournament_pool(tournament_split["player_tournament_pool"])

    db.collection("fee_logs").add({
        "user_id": str(user_id),
        "trade_id": trade_id,
        "profit": profit,
        "total_fee": total_fee,
        "your_fee_base": profit * 0.005,
        "your_fee_tournament": tournament_split["your_cut_from_tournament"],
        "daily_weekly_pool": player_split["daily_weekly_pool"],
        "trophy_reset_pool": player_split["trophy_reset_pool"],
        "timestamp": datetime.utcnow().isoformat()
    })

async def notify_tournament_entry(user_data, tournament_type):
    message = (
        f"You're in!\n"
        f"Tournament: {tournament_type.upper()}\n"
        f"Profit fee: 1.25%\n"
        f"Breakdown:\n"
        f"• 0.25% to platform\n"
        f"• 0.70% to daily/weekly prize pool\n"
        f"• 0.30% to 6-month trophy reset\n"
        f"Good luck, {user_data.get('username', 'Trader')}!"
    )
    await send_telegram_alert(user_data["telegram_id"], message)

async def send_fee_breakdown(user_data):
    message = (
        "Just a reminder:\n"
        "Your tournament profit fee is 1.25%:\n"
        "• 0.25% to us (platform fee)\n"
        "• 0.70% to the live daily/weekly prize pool\n"
        "• 0.30% to the 6-month trophy season reset prize\n"
        "We only profit if you do!"
    )
    await send_telegram_alert(user_data["telegram_id"], message)

def award_trophy(user_data, db):
    user_id = user_data["telegram_id"]
    user_doc = db.collection("users").document(user_id)

    user_info = user_doc.get().to_dict()
    current_trophies = user_info.get("trophies", 0)

    user_doc.update({"trophies": current_trophies + 1})

async def notify_trophy_award(user_data):
    message = (
        "Congrats!\n"
        "You earned a Trophy for profitable tournament trading.\n"
        "Every trophy boosts your ranking for the 6-month grand prize!"
    )
    await send_telegram_alert(user_data["telegram_id"], message)

async def send_trade_signal(user_data, signal):
    message = (
        f"Edge AI Signal:\n"
        f"Trade: {signal['pair']} – {signal['direction'].upper()}\n"
        f"Confidence: {signal['confidence']}%\n"
        f"Suggested Entry: {signal['entry_price']}\n"
        f"Target Profit: {signal['target']} | Stop Loss: {signal['stop_loss']}\n"
        f"Reply with /accept to confirm trade."
    )
    await send_telegram_alert(user_data["telegram_id"], message)

from telegram.ext import CommandHandler

async def accept_trade(update, context):
    telegram_id = update.effective_user.id
    # Fetch user data and latest signal from DB or memory
    signal = get_latest_signal_for_user(telegram_id)
    if signal:
        place_trade(telegram_id, signal)
        await update.message.reply_text("Trade accepted and placed.")
    else:
        await update.message.reply_text("No active trade signal.")

async def send_trade_result(user_data, result):
    message = (
        f"Trade Closed:\n"
        f"{result['pair']} – Result: {result['outcome'].upper()}\n"
        f"Profit/Loss: {result['pnl']:.2f} ZAR\n"
        f"Running Balance: {result['balance']:.2f} ZAR"
    )
    await send_telegram_alert(user_data["telegram_id"], message)

async def edge_ai_emotion_check(user_data, trade_history):
    risky_pattern = detect_emotional_trading(trade_history)
    if risky_pattern:
        message = (
            "Edge AI Warning:\n"
            "We detected risky emotional behavior (e.g. revenge trading, overtrading).\n"
            "Consider taking a break or switching to lower risk mode.\n"
            "Reply with /cooldown to pause trading for 1 hour."
        )
        await send_telegram_alert(user_data["telegram_id"], message)

async def cooldown(update, context):
    telegram_id = update.effective_user.id
    activate_cooldown(telegram_id, duration_minutes=60)
    await update.message.reply_text("Cooldown activated. Trading paused for 1 hour.")

async def edge_ai_emotion_analysis(user_id, user_doc):
        data = user_doc.to_dict()
        trade_history = data.get("trade_history", [])
        recent_trades = trade_history[-5:]

        # Emotion detection logic: overtrading, revenge trading, panic exits
        overtrading = sum(1 for t in recent_trades if t["interval"] < 300) >= 3
        revenge_trading = sum(1 for t in recent_trades if t["result"] == "loss") >= 3
        panic_exit = any(t["profit_pct"] < -5 for t in recent_trades)

        feedback_msgs = []
        if overtrading:
            feedback_msgs.append("You're placing trades too quickly. Breathe and trust your setups.")
        if revenge_trading:
            feedback_msgs.append("It looks like you're revenge trading. Consider taking a break.")
        if panic_exit:
            feedback_msgs.append("You exited a trade too early. Make sure you stick to your plan.")

        if feedback_msgs:
            full_message = "\n".join(feedback_msgs)
            await send_telegram_message(user_id, f"**Edge AI Feedback:**\n{full_message}")
async def edge_ai_confirm_risky_trade(user_id, signal):
            """Prompt user to confirm risky trade patterns before execution."""
            risk_detected = False
            if signal["rsi"] > 80 or signal["rsi"] < 20:
                risk_detected = True

            if risk_detected:
                prompt = (
                    "Edge AI has detected a high-risk trade setup.\n"
                    f"Pair: {signal['pair']}\n"
                    f"RSI: {signal['rsi']}\n"
                    "Are you sure you want to proceed?"
                )
                await send_telegram_message(user_id, prompt + "\nReply with YES to confirm.")

async def monitor_confirmations():
            """Listen for confirmation responses on risky trades."""
            # This is handled by a Telegram command handler where users reply with YES

async def handle_user_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            text = update.message.text.strip().upper()
            if text == "YES":
                # Mark user confirmed
                confirmation_flags[user_id] = True
                await update.message.reply_text("Confirmed. Proceeding with trade.")
            else:
                await update.message.reply_text("Trade cancelled due to no confirmation.")

        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_reply))

 def update_trophy_count(user_id, trophies):
            """Update user's trophy count in Firebase."""
            user_ref = db.collection("users").document(str(user_id))
            user_ref.set({"trophies": firestore.Increment(trophies)}, merge=True)

 def reset_trophies_every_season():
            """Reset all user trophies and rank top 100 for payout."""
            users_ref = db.collection("users")
            all_users = users_ref.stream()
            trophy_leaderboard = []

            for doc in all_users:
                data = doc.to_dict()
                trophies = data.get("trophies", 0)
                trophy_leaderboard.append((doc.id, trophies))

            trophy_leaderboard.sort(key=lambda x: x[1], reverse=True)
            top_100 = trophy_leaderboard[:100]

            season_pool = get_season_pool_amount()
            distribute_trophy_rewards(top_100, season_pool)

            # Reset all trophies
            for user_id, _ in trophy_leaderboard:
                users_ref.document(user_id).update({"trophies": 0})

def get_season_pool_amount():
            """Placeholder to fetch the current 6-month trophy pool balance."""
            return 1000  # Simulated value for now

def distribute_trophy_rewards(top_users, total_amount):
            """Distribute trophy reset rewards to top 100 users."""
            reward_structure = [0.20, 0.15, 0.10] + [0.01]*97  # Descending reward
            for idx, (user_id, _) in enumerate(top_users):
                reward_pct = reward_structure[idx]
                reward = total_amount * reward_pct
                send_telegram_message(user_id, f"You earned {reward:.2f} from the trophy reset pool!")

def create_hall_of_fame_entry(user_id, trophy_count):
            """Add user to hall of fame list after reset."""
            db.collection("hall_of_fame").add({
                "user_id": user_id,
                "trophies": trophy_count,
                "timestamp": datetime.utcnow()
            })

def fetch_hall_of_fame():
    """Retrieve top Hall of Fame entries."""
    entries = db.collection("hall_of_fame").order_by("trophies", direction=firestore.Query.DESCENDING).limit(100).stream()
    leaderboard = []
    for entry in entries:
        data = entry.to_dict()
        leaderboard.append({
            "user_id": data.get("user_id"),
            "trophies": data.get("trophies"),
            "timestamp": data.get("timestamp").strftime("%Y-%m-%d")
        })
    return leaderboard

        @app.route("/hall-of-fame")
def hall_of_fame_route():
    """Web route to show Hall of Fame leaderboard."""
    leaderboard = fetch_hall_of_fame()
    return jsonify(leaderboard)
        async def send_tournament_results():
            """Send final daily/weekly tournament results via Telegram."""
            leaderboard = calculate_tournament_leaderboard()
            for idx, (user_id, score) in enumerate(leaderboard):
                rank = idx + 1
                message = f"**Tournament Result**\nRank: {rank}\nScore: {score}"
                await send_telegram_message(user_id, message)

def calculate_tournament_leaderboard():
            """Compute tournament rankings based on profit %."""
            users = db.collection("users").stream()
            leaderboard = []
            for doc in users:
                data = doc.to_dict()
                profit = data.get("tournament_profit", 0)
                leaderboard.append((doc.id, profit))
            leaderboard.sort(key=lambda x: x[1], reverse=True)
            return leaderboard[:100]

def distribute_tournament_rewards():
            """Distribute rewards based on tournament leaderboard."""
            leaderboard = calculate_tournament_leaderboard()
            total_pool = get_tournament_pool_balance()
            reward_structure = [0.25, 0.15, 0.10] + [0.005]*97

            for idx, (user_id, profit) in enumerate(leaderboard):
                if idx < len(reward_structure):
                    share = total_pool * reward_structure[idx]
                    db.collection("users").document(user_id).set(
                        {"wallet": firestore.Increment(share)}, merge=True)
                    asyncio.run(send_telegram_message(
                        user_id, f"Congrats! You won {share:.2f} in the tournament."))

def get_tournament_pool_balance():
            """Placeholder to fetch current tournament pool total."""
            return 500  # Replace with actual balance logic

def reset_tournament_profits():
            """Clear each user's tournament profits after reward."""
            users = db.collection("users").stream()
            for doc in users:
                db.collection("users").document(doc.id).update({
                    "tournament_profit": 0
                })

def calculate_app_fee(profit_amount):
            """Calculate 0.50% app fee on total profit."""
            return round(profit_amount * 0.005, 2)

def calculate_tournament_cut(profit_amount):
            """Calculate 1.25% total tournament deduction from profits."""
            return round(profit_amount * 0.0125, 2)

def split_tournament_cut(total_cut):
            """Split 1% cut: 70% to tournaments, 30% to trophy pool."""
            tournament_pool = total_cut * 0.70
            trophy_pool = total_cut * 0.30
            return tournament_pool, trophy_pool

def handle_trade_profit_split(user_id, profit_amount):
            """Deduct app fee and split tournament cut on profit."""
            app_fee = calculate_app_fee(profit_amount)
            tournament_cut = calculate_tournament_cut(profit_amount)
            tournament_pool, trophy_pool = split_tournament_cut(tournament_cut)

            net_profit = profit_amount - (app_fee + tournament_cut)

            user_ref = db.collection("users").document(user_id)
            user_ref.set({
                "wallet": firestore.Increment(net_profit),
                "tournament_contribution": firestore.Increment(tournament_pool),
                "trophy_contribution": firestore.Increment(trophy_pool),
            }, merge=True)

            return {
                "net_profit": net_profit,
                "app_fee": app_fee,
                "tournament_cut": tournament_cut,
                "tournament_pool": tournament_pool,
                "trophy_pool": trophy_pool
            }

async def send_profit_summary(user_id, profit_summary):
            """Send a summary of fee breakdown and net gain."""
            msg = (
                f"Trade Result:\n"
                f"Net Profit: {profit_summary['net_profit']:.2f}\n"
                f"App Fee (0.5%): {profit_summary['app_fee']:.2f}\n"
                f"Tournament Contribution: {profit_summary['tournament_cut']:.2f}\n"
                f"  • 70% Daily/Weekly Pool: {profit_summary['tournament_pool']:.2f}\n"
                f"  • 30% Trophy Reset Pool: {profit_summary['trophy_pool']:.2f}"
            )
            await send_telegram_message(user_id, msg)

async def update_trade_result(user_id, profit_amount):
            """Full pipeline: update user profit, fees, pools, and notify."""
            summary = handle_trade_profit_split(user_id, profit_amount)
            await send_profit_summary(user_id, summary)

 def get_user_balance(user_id):
            """Get user wallet balance from Firestore."""
            doc = db.collection("users").document(user_id).get()
            if doc.exists:
                return doc.to_dict().get("wallet", 0)
            return 0

 def get_user_trophies(user_id):
            """Get user's trophy count."""
            doc = db.collection("users").document(user_id).get()
            if doc.exists:
                return doc.to_dict().get("trophies", 0)
            return 0

def increment_user_trophies(user_id, count=1):
            """Increment user's trophies by count."""
            db.collection("users").document(user_id).set(
                {"trophies": firestore.Increment(count)}, merge=True)

def reset_season_rewards():
            """Distribute 6-month trophy reset rewards."""
            leaderboard = fetch_hall_of_fame()
            pool_amount = get_trophy_pool_balance()
            rewards = calculate_reset_reward_distribution(pool_amount)

            for i, player in enumerate(leaderboard):
                user_id = player["user_id"]
                reward = rewards[i] if i < len(rewards) else 0
                db.collection("users").document(user_id).set(
                    {"wallet": firestore.Increment(reward)}, merge=True)
                asyncio.run(send_telegram_message(
                    user_id, f"Season Reset Reward: You earned {reward:.2f} for your trophy rank!"))

def calculate_reset_reward_distribution(pool_total):
            """Tiered distribution for top 100 players."""
            weights = [0.20, 0.15, 0.10] + [0.005]*97
            total_weight = sum(weights)
            return [round(pool_total * (w / total_weight), 2) for w in weights]

 def get_trophy_pool_balance():
            """Placeholder logic for trophy pool total."""
            return 300  # Replace with actual balance logic later

def add_to_trophy_pool(amount):
            """Store trophy pool contributions (mock)."""
            pass  # Replace with DB update if tracking trophy pool per transaction

        @app.route("/simulate_profit", methods=["POST"])
 async def simulate_profit():
            """Simulate a trade profit for testing."""
            data = request.get_json()
            user_id = data["user_id"]
            profit = float(data["profit"])
            await update_trade_result(user_id, profit)
            return jsonify({"status": "done"})

        @app.route("/user_balance/<user_id>")
 def user_balance(user_id):
            """Return wallet balance."""
            balance = get_user_balance(user_id)
            return jsonify({"wallet": balance})

        @app.route("/user_trophies/<user_id>")
 def user_trophies(user_id):
            """Return user trophy count."""
            trophies = get_user_trophies(user_id)
            return jsonify({"trophies": trophies})

        @app.route("/leaderboard")
 def get_leaderboard():
            """Return top 10 profit leaders."""
            users = db.collection("users").order_by(
                "wallet", direction=firestore.Query.DESCENDING).limit(10).stream()
            leaderboard = []
            for doc in users:
                data = doc.to_dict()
                leaderboard.append({
                    "username": data.get("username", "N/A"),
                    "wallet": round(data.get("wallet", 0), 2)
                })
            return jsonify(leaderboard)

 async def start_trophy_season_reset():
            """Reset logic for 6-month trophy season."""
            reset_season_rewards()
            users = db.collection("users").stream()
            for doc in users:
                db.collection("users").document(doc.id).update({
                    "trophies": 0,
                    "trophy_contribution": 0
                })

 def get_user_summary(user_id):
            """Get user's key stats."""
            doc = db.collection("users").document(user_id).get()
            if doc.exists:
                data = doc.to_dict()
                return {
                    "wallet": round(data.get("wallet", 0), 2),
                    "trophies": data.get("trophies", 0),
                    "tournament_contribution": round(data.get("tournament_contribution", 0), 2),
                    "trophy_contribution": round(data.get("trophy_contribution", 0), 2)
                }
            return {}

        @app.route("/user_summary/<user_id>")
        def user_summary(user_id):
            """Return user's full app stats."""
            return jsonify(get_user_summary(user_id))

async def send_user_summary(user_id):
            """Send user's full summary over Telegram."""
            summary = get_user_summary(user_id)
            if summary:
                message = (
                    f"**Your Account Summary**\n"
                    f"Wallet: ${summary['wallet']}\n"
                    f"Trophies: {summary['trophies']}\n"
                    f"Tournament Contribution: ${summary['tournament_contribution']}\n"
                    f"Trophy Pool Contribution: ${summary['trophy_contribution']}"
                )
                await send_telegram_message(user_id, message)
            else:
                await send_telegram_message(user_id, "No user data found.")

async def send_trade_signal(user_id, coin, signal, price):
            """Send a trade signal to user."""
            message = f"Signal for {coin}: {signal.upper()} at ${price}"
            await send_telegram_message(user_id, message)

def analyze_user_behavior(user_id):
            """Mock behavior analysis for Edge AI."""
            data = db.collection("users").document(user_id).get().to_dict()
            trade_count = data.get("trade_count", 0)
            losses = data.get("losses", 0)
            if losses / max(trade_count, 1) > 0.5:
                return "caution"
            return "normal"

async def edge_ai_check(user_id, trade_data):
            """Run smart assistant checks before executing trade."""
            behavior = analyze_user_behavior(user_id)
            if behavior == "caution":
                await send_telegram_message(
                    user_id,
                    f"High loss rate detected. Are you sure you want to proceed with this trade?\n{trade_data}"
                )
            else:
                await send_telegram_message(
                    user_id,
                    f"Trade check passed.\n{trade_data}"
                )

def log_trade(user_id, trade_data):
            """Log trade attempt in user history."""
            db.collection("users").document(user_id).collection("trades").add({
                "timestamp": datetime.utcnow().isoformat(),
                "details": trade_data
            })

async def simulate_edge_ai_trade(user_id, coin, direction, price):
            """Full mock flow using Edge AI support."""
            trade_data = {
                "coin": coin,
                "direction": direction,
                "price": price
            }
            await edge_ai_check(user_id, trade_data)
            log_trade(user_id, trade_data)

        @app.route("/simulate_edge_trade", methods=["POST"])
async def simulate_edge_trade():
            data = request.get_json()
            user_id = data["user_id"]
            coin = data["coin"]
            direction = data["direction"]
            price = data["price"]
            await simulate_edge_ai_trade(user_id, coin, direction, price)
            return jsonify({"status": "Edge AI trade simulated"})

def register_trade_result(user_id, result):
            """Store trade win/loss."""
            db.collection("users").document(user_id).update({
                "trade_count": firestore.Increment(1),
                "losses": firestore.Increment(1 if result == "loss" else 0)
            })

        @app.route("/record_result", methods=["POST"])
def record_result():
            """Record manual trade result."""
            data = request.get_json()
            user_id = data["user_id"]
            result = data["result"]
            register_trade_result(user_id, result)
            return jsonify({"status": "Result recorded"})

def get_recent_trades(user_id):
            """Fetch user's last 5 trades."""
            trades = db.collection("users").document(user_id).collection(
                "trades").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(5).stream()
            return [{
                "time": doc.to_dict().get("timestamp", ""),
                "details": doc.to_dict().get("details", {})
            } for doc in trades]

        @app.route("/recent_trades/<user_id>")
def recent_trades(user_id):
            """Return recent trades."""
            return jsonify(get_recent_trades(user_id))

def calculate_win_ratio(user_id):
            """Calculate user's win ratio from stored stats."""
            user_data = db.collection("users").document(user_id).get().to_dict()
            total_trades = user_data.get("trade_count", 0)
            total_losses = user_data.get("losses", 0)
            if total_trades == 0:
                return 0.0
            wins = total_trades - total_losses
            return round(wins / total_trades, 2)

        @app.route("/win_ratio/<user_id>")
def win_ratio(user_id):
            """Return user's win ratio."""
            ratio = calculate_win_ratio(user_id)
            return jsonify({"win_ratio": ratio})

def assign_trophies(user_id, ratio):
            """Assign trophies based on win ratio."""
            if ratio >= 0.9:
                earned = 5
            elif ratio >= 0.75:
                earned = 3
            elif ratio >= 0.5:
                earned = 1
            else:
                earned = 0
            db.collection("users").document(user_id).update({
                "trophies": firestore.Increment(earned)
            })
            return earned

        @app.route("/assign_trophies/<user_id>")
def assign_trophy(user_id):
            """API to assign trophies after evaluating win ratio."""
            ratio = calculate_win_ratio(user_id)
            earned = assign_trophies(user_id, ratio)
            return jsonify({"status": "trophies_updated", "earned": earned})

def get_top_trophy_holders(limit=100):
            """Return top 100 users by trophy count."""
            users = db.collection("users").order_by(
                "trophies", direction=firestore.Query.DESCENDING).limit(limit).stream()
            return [{"user_id": u.id, **u.to_dict()} for u in users]

        @app.route("/leaderboard")
def leaderboard():
            """Return top players by trophies."""
            top_users = get_top_trophy_holders()
            return jsonify(top_users)

def distribute_season_rewards():
            """Mock distribution for season reset."""
            top_100 = get_top_trophy_holders()
            total_pool = get_current_trophy_pool()
            rewards = []
            for i, user in enumerate(top_100):
                user_reward = round((1.0 / (i + 1)) * total_pool / 5, 2)  # descending weight
                db.collection("users").document(user["user_id"]).update({
                    "wallet": firestore.Increment(user_reward)
                })
                rewards.append({"user": user["user_id"], "reward": user_reward})
            return rewards

        @app.route("/distribute_season_rewards", methods=["POST"])
def api_distribute_season_rewards():
            rewards = distribute_season_rewards()
            return jsonify(rewards)

def reset_trophies_all():
            """Reset trophies for all users at season end."""
            users = db.collection("users").stream()
            for user in users:
                db.collection("users").document(user.id).update({"trophies": 0})
            return "Trophies reset"

        @app.route("/reset_trophies", methods=["POST"])
def api_reset_trophies():
            return jsonify({"status": reset_trophies_all()})

def get_user_wallet(user_id):
            """Get wallet balance."""
            user = db.collection("users").document(user_id).get().to_dict()
            return user.get("wallet", 0.0)

        @app.route("/wallet/<user_id>")
def wallet_balance(user_id):
            balance = get_user_wallet(user_id)
            return jsonify({"wallet": balance})

def add_to_wallet(user_id, amount):
            db.collection("users").document(user_id).update({
                "wallet": firestore.Increment(amount)
            })

@app.route("/add_wallet/<user_id>", methods=["POST"])
def api_add_wallet(user_id):
            data = request.get_json()
            amount = float(data.get("amount", 0.0))
            add_to_wallet(user_id, amount)
            return jsonify({"status": "wallet_updated", "amount_added": amount})

def deduct_from_wallet(user_id, amount):
            db.collection("users").document(user_id).update({
                "wallet": firestore.Increment(-amount)
            })

        @app.route("/deduct_wallet/<user_id>", methods=["POST"])
def api_deduct_wallet(user_id):
            data = request.get_json()
            amount = float(data.get("amount", 0.0))
            deduct_from_wallet(user_id, amount)
            return jsonify({"status": "wallet_deducted", "amount": amount})

        def create_user_if_not_exists(user_id, username=None):
            user_ref = db.collection("users").document(user_id)
            if not user_ref.get().exists:
                user_ref.set({
                    "telegram_id": user_id,
                    "username": username,
                    "wallet": 0.0,
                    "trophies": 0,
                    "trade_count": 0,
                    "losses": 0,
                    "tournament_opt_in": False,
                    "binance_api": {},
                    "luno_api": {}
                })

        @app.route("/create_user/<user_id>", methods=["POST"])
        def api_create_user(user_id):
            data = request.get_json()
            username = data.get("username", None)
            create_user_if_not_exists(user_id, username)
            return jsonify({"status": "user_created"})

        def get_user_data(user_id):
            doc = db.collection("users").document(user_id).get()
            return doc.to_dict() if doc.exists else None

        @app.route("/user_data/<user_id>")
        def api_user_data(user_id):
            data = get_user_data(user_id)
            return jsonify(data if data else {"error": "User not found"})

        def update_api_keys(user_id, binance=None, luno=None):
            updates = {}
            if binance:
                updates["binance_api"] = binance
            if luno:
                updates["luno_api"] = luno
            if updates:
                db.collection("users").document(user_id).update(updates)

        @app.route("/update_keys/<user_id>", methods=["POST"])
        def api_update_keys(user_id):
            data = request.get_json()
            binance = data.get("binance_api")
            luno = data.get("luno_api")
            update_api_keys(user_id, binance, luno)
            return jsonify({"status": "keys_updated"})

        def opt_into_tournament(user_id):
            db.collection("users").document(user_id).update({
                "tournament_opt_in": True
            })

        @app.route("/opt_in_tournament/<user_id>", methods=["POST"])
        def api_opt_in(user_id):
            opt_into_tournament(user_id)
            return jsonify({"status": "opted_in"})

def calculate_tournament_fee(profit):
            return profit * 0.0125  # 1.25%

        def distribute_fees(profit):
            total_fee = calculate_tournament_fee(profit)
            app_fee = profit * 0.005
            tournament_pool = profit * 0.007
            return {
                "total_fee": total_fee,
                "app_fee": app_fee,
                "tournament_pool": tournament_pool
            }

        def split_tournament_pool(pool_amount):
            daily_weekly = pool_amount * 0.7
            trophy_reset = pool_amount * 0.3
            return {
                "daily_weekly": daily_weekly,
                "trophy_reset": trophy_reset
            }

        def reward_trophy_winners():
            users = db.collection("users").get()
            all_users = [(u.id, u.to_dict().get("trophies", 0)) for u in users]
            sorted_users = sorted(all_users, key=lambda x: x[1], reverse=True)
            top_100 = sorted_users[:100]
            rewards = [0.04, 0.03, 0.025] + [0.02]*7 + [0.01]*20 + [0.005]*70
            payouts = []
            for i, (user_id, _) in enumerate(top_100):
                reward = rewards[i] if i < len(rewards) else 0.001
                payouts.append((user_id, reward))
            return payouts

        def send_trophy_rewards():
            payouts = reward_trophy_winners()
            for user_id, percentage in payouts:
                wallet = db.collection("users").document(user_id).get().to_dict().get("wallet", 0.0)
                reward_amount = percentage * trophy_reset_pool
                db.collection("users").document(user_id).update({
                    "wallet": wallet + reward_amount
                })

        def reset_trophies():
            users = db.collection("users").get()
            for user in users:
                db.collection("users").document(user.id).update({"trophies": 0})

        def send_tournament_update(text):
            for chat_id in telegram_chat_ids:
                application.bot.send_message(chat_id=chat_id, text=text)

        @app.route("/trigger_trophy_reset", methods=["POST"])
        def api_trigger_trophy_reset():
            send_trophy_rewards()
            reset_trophies()
            send_tournament_update("Trophy season has reset and top 100 rewards were sent!")
            return jsonify({"status": "reset_complete"})

def track_trade(user_id, result, amount):
            user_ref = db.collection("users").document(user_id)
            user_data = user_ref.get().to_dict()
            new_trade_count = user_data.get("trade_count", 0) + 1
            update = {"trade_count": new_trade_count}

            if result == "loss":
                update["losses"] = user_data.get("losses", 0) + 1
            elif result == "profit":
                fee_summary = distribute_fees(amount)
                app_fee = fee_summary["app_fee"]
                tournament_pool = fee_summary["tournament_pool"]
                split_pool = split_tournament_pool(tournament_pool)
                add_to_wallet(user_id, amount - fee_summary["total_fee"])
                db.collection("app_meta").document("fees").update({
                    "app_total": firestore.Increment(app_fee),
                    "tournament_pool": firestore.Increment(split_pool["daily_weekly"]),
                    "trophy_reset_pool": firestore.Increment(split_pool["trophy_reset"])
                })
                update["trophies"] = user_data.get("trophies", 0) + 1

            user_ref.update(update)

        @app.route("/submit_trade/<user_id>", methods=["POST"])
        def api_submit_trade(user_id):
            data = request.get_json()
            result = data.get("result")
            amount = float(data.get("amount", 0.0))
            track_trade(user_id, result, amount)
            return jsonify({"status": "trade_logged"})

        def get_rankings():
            users = db.collection("users").get()
            rankings = []
            for u in users:
                data = u.to_dict()
                rankings.append({
                    "user_id": u.id,
                    "trophies": data.get("trophies", 0),
                    "username": data.get("username", "N/A"),
                    "wallet": data.get("wallet", 0.0)
                })
            sorted_ranks = sorted(rankings, key=lambda x: x["trophies"], reverse=True)
            return sorted_ranks

        @app.route("/rankings")
        def api_rankings():
            ranks = get_rankings()
            return jsonify(ranks)

def format_rankings(rankings, top_n=10):
            lines = ["Top {} Players:".format(top_n)]
            for i, r in enumerate(rankings[:top_n]):
                lines.append(f"{i+1}. {r['username']} - {r['trophies']} trophies - R{r['wallet']:.2f}")
            return "\n".join(lines)

        def broadcast_rankings():
            top_ranks = get_rankings()
            text = format_rankings(top_ranks, top_n=10)
            for chat_id in telegram_chat_ids:
                application.bot.send_message(chat_id=chat_id, text=text)

        @app.route("/broadcast_ranks")
        def api_broadcast_ranks():
            broadcast_rankings()
            return jsonify({"status": "broadcasted"})

        def daily_tournament_distribute():
            pool_ref = db.collection("app_meta").document("fees")
            pool_data = pool_ref.get().to_dict()
            daily_pool = pool_data.get("tournament_pool", 0.0)

            if daily_pool < 10:
                return "Pool too small to distribute."

            rankings = get_rankings()
            top_100 = rankings[:100]
            rewards = [0.04, 0.03, 0.025] + [0.02]*7 + [0.01]*20 + [0.005]*70
            for i, r in enumerate(top_100):
                percent = rewards[i] if i < len(rewards) else 0.001
                reward_amt = daily_pool * percent
                db.collection("users").document(r["user_id"]).update({
                    "wallet": firestore.Increment(reward_amt)
                })

            pool_ref.update({"tournament_pool": 0.0})
            broadcast_rankings()
            return "Daily rewards distributed."

        @app.route("/daily_tournament_payout", methods=["POST"])
        def api_daily_payout():
            result = daily_tournament_distribute()
            return jsonify({"result": result})

def get_user_summary(user_id):
            user_data = db.collection("users").document(user_id).get().to_dict()
            return {
                "username": user_data.get("username", "N/A"),
                "wallet": user_data.get("wallet", 0.0),
                "trophies": user_data.get("trophies", 0),
                "trades": user_data.get("trade_count", 0),
                "losses": user_data.get("losses", 0)
            }

        @app.route("/user_summary/<user_id>")
        def api_user_summary(user_id):
            data = get_user_summary(user_id)
            return jsonify(data)

        def send_personal_summary(chat_id, user_id):
            summary = get_user_summary(user_id)
            message = (
                f"**Your Summary**\n"
                f"Username: {summary['username']}\n"
                f"Trophies: {summary['trophies']}\n"
                f"Wallet: R{summary['wallet']:.2f}\n"
                f"Trades: {summary['trades']} | Losses: {summary['losses']}"
            )
            application.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

        @app.route("/send_my_summary", methods=["POST"])
        def api_send_my_summary():
            data = request.get_json()
            telegram_id = str(data.get("telegram_id"))
            user_id = telegram_to_user.get(telegram_id)
            if not user_id:
                return jsonify({"error": "Not linked"})
            send_personal_summary(telegram_id, user_id)
            return jsonify({"status": "sent"})

def reset_trophy_cycle():
            rankings = get_rankings()
            top_100 = rankings[:100]
            reset_pool_ref = db.collection("app_meta").document("fees")
            reset_data = reset_pool_ref.get().to_dict()
            reset_pool = reset_data.get("reset_pool", 0.0)

            if reset_pool < 50:
                return "Not enough in reset pool."

            reward_distribution = [0.08, 0.07, 0.06] + [0.05]*7 + [0.025]*20 + [0.01]*70
            for i, player in enumerate(top_100):
                if i >= len(reward_distribution):
                    break
                reward = reset_pool * reward_distribution[i]
                db.collection("users").document(player["user_id"]).update({
                    "wallet": firestore.Increment(reward)
                })

            reset_pool_ref.update({"reset_pool": 0.0})

            for player in rankings:
                db.collection("users").document(player["user_id"]).update({"trophies": 0})

            return "Reset rewards given and trophies cleared."

        @app.route("/season_reset", methods=["POST"])
        def api_reset_season():
            result = reset_trophy_cycle()
            return jsonify({"result": result})

def calculate_trade_fee(profit):
            if profit <= 0:
                return 0.0
            app_fee = profit * 0.005  # 0.50%
            tournament_fee = profit * 0.01  # 1.0%
            reset_cut = tournament_fee * 0.30  # 30% to trophy reset
            daily_cut = tournament_fee * 0.70  # 70% to daily/weekly
            return app_fee, daily_cut, reset_cut

        def apply_profit_distribution(user_id, profit):
            app_fee, daily, reset = calculate_trade_fee(profit)
            user_ref = db.collection("users").document(user_id)
            user_ref.update({
                "wallet": firestore.Increment(profit - app_fee - daily - reset),
                "profit": firestore.Increment(profit),
                "trade_count": firestore.Increment(1)
            })

            meta_ref = db.collection("app_meta").document("fees")
            meta_ref.update({
                "app_fee": firestore.Increment(app_fee),
                "tournament_pool": firestore.Increment(daily),
                "reset_pool": firestore.Increment(reset)
            })

        @app.route("/mock_trade", methods=["POST"])
        def mock_trade():
            data = request.get_json()
            user_id = data.get("user_id")
            profit = float(data.get("profit"))
            apply_profit_distribution(user_id, profit)
            return jsonify({"status": "applied", "net_profit": profit})

def tournament_cleanup():
            # Reset tournament-specific data for the new round
            today = datetime.datetime.now().date()
            last_cleanup = db.collection("app_meta").document("tournament")
            last_cleanup_data = last_cleanup.get().to_dict()
            last_date = last_cleanup_data.get("last_reset", None)

            if last_date != today:
                db.collection("app_meta").document("tournament").update({
                    "last_reset": today,
                    "daily_winners": [],
                    "weekly_winners": []
                })

                # Notify players of the reset
                notify_players_of_tournament_reset()

        def notify_players_of_tournament_reset():
            users_ref = db.collection("users").stream()
            for user in users_ref:
                try:
                    telegram_send_message(user.id, "Tournament reset! New day, new chances!")
                except Exception as e:
                    print(f"Error sending notification: {e}")

        @app.route("/cleanup_tournament", methods=["POST"])
        def api_cleanup_tournament():
            tournament_cleanup()
            return jsonify({"status": "Tournament reset and players notified."})

def check_for_arbitrage_opportunity():
            arbitrage_gap = 0.02  # 2% price difference
            binance_data = get_binance_prices()
            luno_data = get_luno_prices()

            opportunities = []

            for pair in binance_data:
                binance_price = binance_data[pair]
                luno_price = luno_data.get(pair)

                if luno_price:
                    price_diff = abs(binance_price - luno_price) / binance_price
                    if price_diff >= arbitrage_gap:
                        opportunities.append({
                            "pair": pair,
                            "binance_price": binance_price,
                            "luno_price": luno_price,
                            "price_diff": price_diff
                        })

            return opportunities

        def execute_arbitrage_trade(pair, binance_price, luno_price):
            # Perform the trade based on the higher price (buy from lower, sell at higher)
            if binance_price < luno_price:
                # Buy on Binance and sell on Luno
                place_binance_order(pair, "buy", binance_price)
                place_luno_order(pair, "sell", luno_price)
            else:
                # Buy on Luno and sell on Binance
                place_luno_order(pair, "buy", luno_price)
                place_binance_order(pair, "sell", binance_price)

        def place_binance_order(pair, side, price):
            # Example of how orders might be placed using Binance API
            binance_api.place_order(pair, side, price)

        def place_luno_order(pair, side, price):
            # Example of how orders might be placed using Luno API
            luno_api.place_order(pair, side, price)

        @app.route("/arbitrage_check", methods=["POST"])
        def arbitrage_check():
            opportunities = check_for_arbitrage_opportunity()
            if opportunities:
                for opp in opportunities:
                    execute_arbitrage_trade(opp["pair"], opp["binance_price"], opp["luno_price"])
                return jsonify({"status": "Arbitrage trades executed", "opportunities": opportunities})
            else:
                return jsonify({"status": "No arbitrage opportunities found"})

def fetch_and_send_trade_signal():
            # Fetch signal from the trading algorithm or AI model
            signal = get_trade_signal_from_ai()

            # Notify users about the trade signal
            users_ref = db.collection("users").stream()
            for user in users_ref:
                telegram_send_message(user.id, f"New trade signal: {signal}")

            return "Trade signal sent to all users"

        def get_trade_signal_from_ai():
            # Placeholder for actual AI-based trade signal generator
            return "Buy BTC/USDT at 56000, sell at 57000"

        @app.route("/send_trade_signal", methods=["POST"])
        def send_trade_signal():
            result = fetch_and_send_trade_signal()
            return jsonify({"status": result})

def monitor_trade_success():
            # Check for successful trades and notify user
            successful_trades = get_successful_trades()

            for trade in successful_trades:
                user_id = trade["user_id"]
                profit = trade["profit"]

                # Update wallet balance and notify the user
                db.collection("users").document(user_id).update({
                    "wallet": firestore.Increment(profit)
                })
                telegram_send_message(user_id, f"Your trade was successful! You earned {profit}.")

            return "Trade success monitored and users notified"

        def get_successful_trades():
            # Placeholder function to retrieve successful trades
            return [
                {"user_id": "123", "profit": 150},
                {"user_id": "456", "profit": 200}
            ]

        @app.route("/monitor_success", methods=["POST"])
        def monitor_success():
            result = monitor_trade_success()
            return jsonify({"status": result})

def user_leaderboard():
            users_ref = db.collection("users").order_by("profit", direction=firestore.Query.DESCENDING).limit(10).stream()
            leaderboard = [{"username": user.id, "profit": user.to_dict().get("profit")} for user in users_ref]
            return leaderboard

        @app.route("/leaderboard", methods=["GET"])
        def api_leaderboard():
            leaderboard = user_leaderboard()
            return jsonify({"leaderboard": leaderboard})

def get_player_trophies(user_id):
            user_ref = db.collection("users").document(user_id)
            user_data = user_ref.get().to_dict()
            return user_data.get("trophies", 0)

        @app.route("/player_trophies/<user_id>", methods=["GET"])
        def api_player_trophies(user_id):
            trophies = get_player_trophies(user_id)
            return jsonify({"user_id": user_id, "trophies": trophies})

def set_trophy_for_user(user_id, trophy_count):
            user_ref = db.collection("users").document(user_id)
            user_ref.update({"trophies": trophy_count})

        @app.route("/set_trophy/<user_id>", methods=["POST"])
        def api_set_trophy(user_id):
            data = request.get_json()
            trophy_count = data.get("trophy_count")
            set_trophy_for_user(user_id, trophy_count)
            return jsonify({"status": f"Trophy count for {user_id} updated to {trophy_count}"})

def adjust_wallet_balance(user_id, amount):
            user_ref = db.collection("users").document(user_id)
            user_ref.update({"wallet": firestore.Increment(amount)})

        @app.route("/adjust_wallet/<user_id>", methods=["POST"])
        def api_adjust_wallet(user_id):
            data = request.get_json()
            amount = float(data.get("amount"))
            adjust_wallet_balance(user_id, amount)
            return jsonify({"status": f"Wallet balance for {user_id} adjusted by {amount}"})

def track_trade_activity(user_id, action, details):
            trade_ref = db.collection("trade_activity").document()
            trade_ref.set({
                "user_id": user_id,
                "action": action,
                "details": details,
                "timestamp": firestore.SERVER_TIMESTAMP
            })

        @app.route("/track_trade", methods=["POST"])
        def api_track_trade():
            data = request.get_json()
            user_id = data.get("user_id")
            action = data.get("action")
            details = data.get("details")
            track_trade_activity(user_id, action, details)
            return jsonify({"status": "Trade activity tracked"})

def monitor_profit_margin():
            users_ref = db.collection("users").stream()
            for user in users_ref:
                user_data = user.to_dict()
                if user_data.get("profit") < 0:
                    telegram_send_message(user.id, "Your current balance is negative! Review your trades.")

        @app.route("/monitor_profit", methods=["POST"])
        def api_monitor_profit():
            monitor_profit_margin()
            return jsonify({"status": "Profit margin monitoring complete"})

def get_trade_history(user_id):
            trades_ref = db.collection("trade_activity").where("user_id", "==", user_id).stream()
            trade_history = [{"action": trade.to_dict()["action"], "details": trade.to_dict()["details"]} for trade in trades_ref]
            return trade_history

        @app.route("/trade_history/<user_id>", methods=["GET"])
        def api_trade_history(user_id):
            trade_history = get_trade_history(user_id)
            return jsonify({"user_id": user_id, "trade_history": trade_history})

def fetch_current_wallet_balance(user_id):
            user_ref = db.collection("users").document(user_id)
            user_data = user_ref.get().to_dict()
            return user_data.get("wallet", 0.0)

        @app.route("/wallet_balance/<user_id>", methods=["GET"])
        def api_wallet_balance(user_id):
            balance = fetch_current_wallet_balance(user_id)
            return jsonify({"user_id": user_id, "wallet_balance": balance})

def generate_wallet_report():
            all_users_ref = db.collection("users").stream()
            report = []
            for user in all_users_ref:
                user_data = user.to_dict()
                report.append({
                    "user_id": user.id,
                    "wallet_balance": user_data.get("wallet"),
                    "profit": user_data.get("profit")
                })
            return report

        @app.route("/wallet_report", methods=["GET"])
        def api_wallet_report():
            report = generate_wallet_report()
            return jsonify({"report": report})

def fetch_app_statistics():
            total_users = len(db.collection("users").stream())
            total_profits = sum([user.to_dict().get("profit", 0) for user in db.collection("users").stream()])
            total_wallets = sum([user.to_dict().get("wallet", 0) for user in db.collection("users").stream()])
            return {
                "total_users": total_users,
                "total_profits": total_profits,
                "total_wallets": total_wallets
            }

        @app.route("/app_statistics", methods=["GET"])
        def api_app_statistics():
            stats = fetch_app_statistics()
            return jsonify({"statistics": stats})

