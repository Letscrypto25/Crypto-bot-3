import logging
import requests
import pandas as pd
from binance.client import Client as BinanceClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --- Binance Price Fetcher ---
def get_binance_price(symbol="BTCUSDT", api_key=None, api_secret=None):
    """
    Fetch the latest price for the given symbol from Binance.
    symbol should be Binance format like "BTCUSDT"
    """
    try:
        client = BinanceClient(api_key=api_key, api_secret=api_secret)
        ticker = client.get_symbol_ticker(symbol=symbol)
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
def get_price_history(symbol="BTCUSDT", interval="1h", limit=100, api_key=None, api_secret=None, indicators=False):
    """
    Fetch historical candlestick data from Binance.
    Returns a list of close prices, optionally with SMA/EMA/RSI as a pandas DataFrame.
    """
    try:
        client = BinanceClient(api_key=api_key, api_secret=api_secret)
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)

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
    """
    Fetch the latest price for the given pair from Luno.
    """
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

# --- User Balance Fetcher for Binance ---
def get_user_balance(user, asset="USDT"):
    """
    Get free balance of the given asset for the user on Binance.
    """
    try:
        client = BinanceClient(api_key=user["binance_api_key"], api_secret=user["binance_api_secret"])
        balance = client.get_asset_balance(asset=asset)
        free_balance = float(balance['free']) if balance else 0.0
        logger.info(f"[{user['user_id']}] Binance {asset} balance: {free_balance}")
        return free_balance
    except Exception as e:
        logger.error(f"Failed to get user balance for {asset}: {e}")
        return 0.0

# --- Price Change Calculator ---
def get_price_change(user, symbol, timeframe="1h"):
    """
    Calculates % price change over the last 2 candles on Binance.
    """
    try:
        client = BinanceClient(api_key=user["binance_api_key"], api_secret=user["binance_api_secret"])
        klines = client.get_klines(symbol=symbol, interval=timeframe, limit=2)

        if len(klines) < 2:
            return 0

        open_price = float(klines[0][1])
        close_price = float(klines[1][4])
        change = (close_price - open_price) / open_price
        logger.info(f"[{user['user_id']}] Price change for {symbol}: {change*100:.2f}%")
        return change
    except Exception as e:
        logger.error(f"Error getting price change for {symbol}: {e}")
        return 0

# --- Trade on Binance ---
def trade_on_binance(user, action="buy", symbol="BTCUSDT", amount=None):
    """
    Places a market buy or sell order on Binance.
    For buy: amount is quote order qty (e.g., USDT)
    For sell: amount is base asset quantity
    """
    try:
        client = BinanceClient(api_key=user["binance_api_key"], api_secret=user["binance_api_secret"])

        if action == "buy":
            balance = get_user_balance(user, asset='USDT')
            if balance < 10:
                return f"[{user['user_id']}] Insufficient USDT balance"

            quote_qty = amount or 10
            order = client.order_market_buy(symbol=symbol, quoteOrderQty=quote_qty)

        elif action == "sell":
            base_asset = symbol[:-4] if symbol.endswith("USDT") else symbol.split("USDT")[0]
            base_balance = get_user_balance(user, asset=base_asset)
            if base_balance < 0.0001:
                return f"[{user['user_id']}] Insufficient {base_asset} balance"

            sell_qty = amount or base_balance
            order = client.order_market_sell(symbol=symbol, quantity=sell_qty)

        else:
            return f"[{user['user_id']}] Invalid action: {action}"

        logger.info(f"[{user['user_id']}] Binance {action.upper()} order placed: {order['orderId']}")
        return f"[{user['user_id']}] Binance {action.upper()} order placed: {order['orderId']}"

    except Exception as e:
        logger.error(f"Binance trade error for user {user['user_id']}: {e}")
        return str(e)

# --- Trade on Luno ---
def trade_on_luno(user, action="buy", amount=None):
    """
    Places a buy or sell order on Luno.
    Note: Luno's API expects POST to https://api.luno.com/api/1/buy or sell endpoint.
    """
    try:
        if action not in ['buy', 'sell']:
            return f"[{user['user_id']}] Invalid Luno action: {action}"

        url = f'https://api.luno.com/api/1/{action}'
        auth = (user["luno_api_key"], user["luno_api_secret"])
        counter_volume = str(amount or 200)  # default 200 ZAR or similar

        data = {
            "pair": "XBTZAR",
            "type": action.upper(),
            "counter_volume": counter_volume
        }

        response = requests.post(url, auth=auth, data=data)
        response.raise_for_status()
        result = response.json()

        order_id = result.get('order_id', 'No order ID')
        logger.info(f"[{user['user_id']}] Luno {action.upper()} order placed: {order_id}")
        return f"[{user['user_id']}] Luno {action.upper()} order placed: {order_id}"

    except Exception as e:
        logger.error(f"Luno trade error for user {user['user_id']}: {e}")
        return str(e)
