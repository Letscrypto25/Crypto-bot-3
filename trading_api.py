import logging
import requests
import pandas as pd
from binance.client import Client as BinanceClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --- Binance Price Fetcher ---
def get_binance_price(symbol="BTC/USDT", api_key=None, api_secret=None):
    try:
        client = BinanceClient(api_key=api_key, api_secret=api_secret)
        symbol_binance = symbol.replace("/", "")
        ticker = client.get_symbol_ticker(symbol=symbol_binance)
        price = float(ticker['price'])
        logger.info(f"Binance price for {symbol}: {price}")
        return price
    except Exception as e:
        logger.error(f"Failed to get Binance price for {symbol}: {e}")
        return None

# --- RSI Indicator with Pandas ---
def get_rsi(prices, period=14):
    """
    Calculates RSI (Relative Strength Index) using pandas.
    Args:
        prices (list or pd.Series): Closing prices, most recent last.
        period (int): RSI period, default 14.
    Returns:
        float: RSI value between 0 and 100.
    """
    if isinstance(prices, list):
        prices = pd.Series(prices)

    if len(prices) < period + 1:
        raise ValueError("Not enough price data to calculate RSI")

    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return round(rsi.iloc[-1], 2)

# --- Binance Historical Price Fetcher + Indicators ---
def get_price_history(symbol="BTC/USDT", interval="1h", limit=100, api_key=None, api_secret=None, indicators=False):
    """
    Fetch historical candlestick data from Binance.
    Returns a list of close prices, optionally with SMA/EMA as a pandas DataFrame.
    """
    try:
        client = BinanceClient(api_key=api_key, api_secret=api_secret)
        symbol_binance = symbol.replace("/", "")
        klines = client.get_klines(symbol=symbol_binance, interval=interval, limit=limit)

        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'
        ])

        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['close'] = df['close'].astype(float)

        if indicators:
            df['SMA_10'] = df['close'].rolling(window=10).mean()
            df['EMA_10'] = df['close'].ewm(span=10, adjust=False).mean()
            df['RSI_14'] = get_rsi(df['close'])

        logger.info(f"Retrieved {len(df)} historical candles for {symbol}")
        return df if indicators else df['close'].tolist()

    except Exception as e:
        logger.error(f"Failed to get price history for {symbol}: {e}")
        return [] if not indicators else pd.DataFrame()

# --- Luno Price Fetcher ---
def get_luno_price(pair="XBTZAR"):
    try:
        response = requests.get(f"https://api.luno.com/api/1/ticker?pair={pair}")
        response.raise_for_status()
        data = response.json()
        price = float(data.get("last_trade"))
        logger.info(f"Luno price for {pair}: {price}")
        return price
    except Exception as e:
        logger.error(f"Failed to get Luno price for {pair}: {e}")
        return None

# --- Price Change Calculator ---
def get_price_change(user, symbol, timeframe="1h"):
    """
    Calculates % price change over the last 2 candles.
    """
    try:
        client = BinanceClient(api_key=user["binance_api_key"], api_secret=user["binance_api_secret"])
        symbol_binance = symbol.replace("/", "")
        klines = client.get_klines(symbol=symbol_binance, interval=timeframe, limit=2)

        if len(klines) < 2:
            return 0

        open_price = float(klines[0][1])
        close_price = float(klines[1][4])
        change = (close_price - open_price) / open_price
        return change
    except Exception as e:
        logger.error(f"Error getting price change for {symbol}: {e}")
        return 0

# --- Trade on Binance ---
def trade_on_binance(user, action="buy", symbol="BTC/USDT", amount=None):
    try:
        client = BinanceClient(api_key=user["binance_api_key"], api_secret=user["binance_api_secret"])
        symbol_binance = symbol.replace("/", "")
        
        if action == "buy":
            balance = client.get_asset_balance(asset='USDT')
            usdt_balance = float(balance['free']) if balance else 0

            if usdt_balance < 10:
                return f"[{user['user_id']}] Insufficient USDT balance"

            quote_qty = amount or 10
            order = client.order_market_buy(symbol=symbol_binance, quoteOrderQty=quote_qty)

        elif action == "sell":
            base_asset = symbol.split("/")[0]
            balance = client.get_asset_balance(asset=base_asset)
            base_balance = float(balance['free']) if balance else 0

            if base_balance < 0.0001:
                return f"[{user['user_id']}] Insufficient {base_asset} balance"

            sell_qty = amount or base_balance
            order = client.order_market_sell(symbol=symbol_binance, quantity=sell_qty)

        else:
            return f"[{user['user_id']}] Invalid action: {action}"

        return f"[{user['user_id']}] Binance {action.upper()} order placed: {order['orderId']}"

    except Exception as e:
        logger.error(f"Binance trade error for user {user['user_id']}: {e}")
        return str(e)

# --- Trade on Luno ---
def trade_on_luno(user, action="buy", amount=None):
    try:
        url = 'https://api.luno.com/api/1/' + action
        auth = (user["luno_api_key"], user["luno_api_secret"])
        counter_volume = str(amount or 200)

        data = {
            "pair": "XBTZAR",
            "type": action.upper(),
            "counter_volume": counter_volume
        }

        response = requests.post(url, auth=auth, data=data)
        response.raise_for_status()
        result = response.json()

        return f"[{user['user_id']}] Luno {action.upper()} order placed: {result.get('order_id', 'No order ID')}"

    except Exception as e:
        logger.error(f"Luno trade error for user {user['user_id']}: {e}")
        return str(e)
