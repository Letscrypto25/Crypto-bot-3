from exchanges import luno_binance

SUPPORTED_EXCHANGES = ["luno", "binance"]

def get_balance(user_id: str, source: str) -> dict:
    """
    Unified balance fetcher from Binance or Luno.

    Args:
        user_id (str): Telegram user ID
        source (str): 'luno' or 'binance'

    Returns:
        dict: e.g., {'BTC': 0.01, 'ETH': 2.3}
    """
    source = source.lower()

    if source not in SUPPORTED_EXCHANGES:
        raise ValueError(f"Unsupported exchange: {source}")

    return luno_binance.get_balance(user_id, source)
