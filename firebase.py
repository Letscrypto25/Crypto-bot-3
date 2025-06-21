import base64
import json
import os
import firebase_admin
from firebase_admin import credentials, db

# === Get Firebase credentials from environment ===
raw_creds = os.getenv("FIREBASE_CREDENTIALS_ENCODED")
if not raw_creds:
    raise Exception("❌ FIREBASE_CREDENTIALS_ENCODED is not set!")

# === Try to load raw JSON or decode if base64 ===
try:
    # Try plain JSON first
    creds_dict = json.loads(raw_creds)
    print("[DEBUG] Firebase credentials loaded as JSON.")
except json.JSONDecodeError:
    try:
        # Try decoding base64
        decoded = base64.b64decode(raw_creds).decode()
        creds_dict = json.loads(decoded)
        print("[DEBUG] Firebase credentials decoded from base64.")
    except Exception as e:
        raise Exception(f"❌ Failed to parse Firebase credentials: {e}")

# === Initialize Firebase ===
if not firebase_admin._apps:
    cred = credentials.Certificate(creds_dict)
    firebase_admin.initialize_app(cred, {
        "databaseURL": os.getenv("FIREBASE_DATABASE_URL")
    })
