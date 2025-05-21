import logging
import requests
from binance.client import Client as BinanceClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def trade_on_binance(user, action="buy", symbol="BTC/USDT", amount=None):
    """Place a market trade on Binance."""
    try:
        client = BinanceClient(api_key=user["binance_api_key"], api_secret=user["binance_api_secret"])
        symbol_binance = symbol.replace("/", "")
        
        if action == "buy":
            balance = client.get_asset_balance(asset='USDT')
            usdt_balance = float(balance['free']) if balance else 0

            if usdt_balance < 10:
                return f"[{user['user_id']}] Insufficient USDT balance"

            quote_qty = amount or 10  # Default buy with $10
            order = client.order_market_buy(symbol=symbol_binance, quoteOrderQty=quote_qty)

        elif action == "sell":
            balance = client.get_asset_balance(asset='BTC')
            btc_balance = float(balance['free']) if balance else 0

            if btc_balance < 0.0001:
                return f"[{user['user_id']}] Insufficient BTC balance"

            sell_qty = amount or btc_balance
            order = client.order_market_sell(symbol=symbol_binance, quantity=sell_qty)

        else:
            return f"[{user['user_id']}] Invalid action: {action}"

        return f"[{user['user_id']}] Binance {action.capitalize()} order placed: {order['orderId']}"

    except Exception as e:
        logger.error(f"Binance trade error for user {user['user_id']}: {e}")
        return str(e)

def trade_on_luno(user, action="buy", amount=None):
    """Place a market trade on Luno (XBTZAR)."""
    try:
        url = 'https://api.luno.com/api/1/' + action
        auth = (user["luno_api_key"], user["luno_api_secret"])
        counter_volume = str(amount or 200)  # Default ZAR amount if not given

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
