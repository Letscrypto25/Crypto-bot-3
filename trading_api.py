import logging
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException

logger = logging.getLogger(__name__)

def get_price_change(symbol: str, client: BinanceClient) -> float:
    try:
        ticker = client.get_ticker(symbol=symbol)
        return float(ticker['priceChangePercent'])
    except Exception as e:
        logger.error(f"Failed to get price change for {symbol}: {e}")
        return 0.0

def get_user_balance(user: dict, asset: str = 'USDT', exchange: str = 'binance') -> float:
    """
    Fetches free balance of a given asset from user's exchange account.
    """
    try:
        if exchange == 'binance':
            client = BinanceClient(api_key=user["binance_api_key"], api_secret=user["binance_api_secret"])
            balance = client.get_asset_balance(asset=asset)
            return float(balance['free']) if balance else 0.0
        elif exchange == 'luno':
            # Placeholder for Luno logic
            logger.warning("Luno balance retrieval not yet implemented.")
            return 0.0
        else:
            logger.error(f"Unsupported exchange: {exchange}")
            return 0.0
    except Exception as e:
        logger.error(f"Error getting balance for user {user.get('user_id', 'unknown')} on {exchange}: {e}")
        return 0.0

def trade_on_binance(user: dict, action: str, symbol: str, amount: float) -> dict:
    try:
        client = BinanceClient(api_key=user["binance_api_key"], api_secret=user["binance_api_secret"])
        asset = symbol.replace("USDT", "")
        usdt_balance = get_user_balance(user, asset="USDT", exchange="binance")
        asset_balance = get_user_balance(user, asset=asset, exchange="binance")

        if action == "buy":
            if usdt_balance < amount:
                return {"error": f"Not enough USDT to buy. Available: {usdt_balance}"}
            order = client.order_market_buy(symbol=symbol, quoteOrderQty=amount)
        elif action == "sell":
            if asset_balance <= 0:
                return {"error": f"Not enough {asset} to sell. Available: {asset_balance}"}
            order = client.order_market_sell(symbol=symbol, quantity=asset_balance)
        else:
            return {"error": f"Invalid action: {action}"}
        return {"status": "success", "order": order}
    except BinanceAPIException as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
