import logging
import requests
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
