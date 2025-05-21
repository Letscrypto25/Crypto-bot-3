import logging
import requests
from binance.client import Client as BinanceClient

logger = logging.getLogger(__name__)

def trade_on_binance(user):
    try:
        client = BinanceClient(api_key=user["binance_api_key"], api_secret=user["binance_api_secret"])

        balance = client.get_asset_balance(asset='USDT')
        usdt_balance = float(balance['free']) if balance else 0

        if usdt_balance < 10:
            return "Insufficient USDT balance"

        order = client.order_market_buy(
            symbol='BTCUSDT',
            quoteOrderQty=10
        )
        return f"Binance Buy order placed: {order['orderId']}"
    except Exception as e:
        logger.error(f"Binance trade error for user {user['user_id']}: {e}")
        return str(e)

def trade_on_luno(user):
    try:
        url = 'https://api.luno.com/api/1/buy'
        auth = (user["luno_api_key"], user["luno_api_secret"])
        data = {
            "pair": "XBTZAR",
            "type": "BUY",
            "counter_volume": "200"
        }

        response = requests.post(url, auth=auth, data=data)
        response.raise_for_status()
        result = response.json()
        return f"Luno Buy order placed: {result.get('order_id', 'No order ID')}"
    except Exception as e:
        logger.error(f"Luno trade error for user {user['user_id']}: {e}")
        return str(e)

