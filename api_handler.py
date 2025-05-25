import logging
import requests
import hmac
import hashlib
import time

from firebase_admin import db

logger = logging.getLogger(__name__)
firebase_ref = db.reference("users")

# --------------------------
# Binance API Validation
# --------------------------
def validate_binance_api(api_key: str, secret: str) -> bool:
    try:
        base_url = "https://api.binance.com"
        endpoint = "/api/v3/account"
        timestamp = int(time.time() * 1000)
        query_string = f'timestamp={timestamp}'
        signature = hmac.new(
            secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        headers = {'X-MBX-APIKEY': api_key}
        url = f"{base_url}{endpoint}?{query_string}&signature={signature}"
        response = requests.get(url, headers=headers)
        return response.status_code == 200
    except Exception as e:
        logger.exception("Binance API validation failed")
        return False

# --------------------------
# Luno API Validation
# --------------------------
def validate_luno_api(api_key: str, secret: str) -> bool:
    try:
        response = requests.get(
            "https://api.luno.com/api/1/balance",
            auth=(api_key, secret)
        )
        return response.status_code == 200
    except Exception as e:
        logger.exception("Luno API validation failed")
        return False

# --------------------------
# Store API Keys (securely)
# --------------------------
def store_api_credentials(user_id: str, exchange: str, api_key: str, secret: str) -> bool:
    try:
        firebase_ref.child(user_id).update({
            "exchange": exchange,
            "api_key": api_key,
            "secret": secret
        })
        return True
    except Exception as e:
        logger.exception("Failed to store API credentials")
        return False