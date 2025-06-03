import base64
import json
import json
import firebase_admin
from firebase_admin import credentials, db
import os

# Load Firebase credentials directly from environment variable
firebase_creds = os.getenv("FIREBASE_CREDENTIALS_ENCODED")  # This is no longer encoded, it's the raw JSON

if not firebase_creds:
    raise Exception("FIREBASE_CREDENTIALS_ENCODED is not set!")

creds_dict = json.loads(firebase_creds)

# Initialize Firebase app
if not firebase_admin._apps:
    cred = credentials.Certificate(creds_dict)
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.getenv("FIREBASE_DATABASE_URL")
    })

def log_trade(trade_data):
    ref = db.reference("/trades")
    ref.push(trade_data)

def get_recent_trades(limit=10):
    ref = db.reference("/trades")
    snapshot = ref.order_by_key().limit_to_last(limit).get()
    return snapshot if snapshot else {}

def store_stat(path, data):
    ref = db.reference(path)
    ref.set(data)

def get_stat(path):
    ref = db.reference(path)
    return ref.get()
