import requests
import os

def get_luno_price(pair="XBTZAR"):
    try:
        response = requests.get(f"https://api.luno.com/api/1/ticker?pair={pair}")
        data = response.json()
        return float(data["ask"]), float(data["bid"])
    except Exception as e:
        return None, None

def get_binance_price(symbol="BTCUSDT"):
    try:
        response = requests.get(f"https://api.binance.com/api/v3/ticker/bookTicker?symbol={symbol}")
        data = response.json()
        return float(data["askPrice"]), float(data["bidPrice"])
    except Exception as e:
        return None, None

def calculate_arbitrage(luno_ask, luno_bid, binance_ask, binance_bid, zar_usd_rate):
    if not all([luno_ask, luno_bid, binance_ask, binance_bid, zar_usd_rate]):
        return None

    # Convert Binance to ZAR
    binance_ask_zar = binance_ask * zar_usd_rate
    binance_bid_zar = binance_bid * zar_usd_rate

    opportunities = {}

    if binance_ask_zar < luno_bid:
        profit = ((luno_bid - binance_ask_zar) / binance_ask_zar) * 100
        opportunities["binance_to_luno"] = round(profit, 2)

    if luno_ask < binance_bid_zar:
        profit = ((binance_bid_zar - luno_ask) / luno_ask) * 100
        opportunities["luno_to_binance"] = round(profit, 2)

    return opportunities
