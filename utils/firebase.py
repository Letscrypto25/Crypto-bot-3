# utils/firebase.py

from firebase_admin import db

def migrate_keys(user_id: str):
    ref = db.reference(f"users/{user_id}")
    data = ref.get()

    if not data:
        return

    # Get old values
    old_key = data.get("api_key")
    old_secret = data.get("api_secret")

    # Skip if already migrated or missing
    if not old_key or not old_secret:
        return

    updates = {}

    if not data.get("luno_api_key"):
        updates["luno_api_key"] = old_key
    if not data.get("luno_api_secret"):
        updates["luno_api_secret"] = old_secret

    if not data.get("binance_api_key"):
        updates["binance_api_key"] = old_key
    if not data.get("binance_api_secret"):
        updates["binance_api_secret"] = old_secret

    # Optionally remove old keys
    updates["api_key"] = None
    updates["api_secret"] = None

    if updates:
        ref.update(updates)
        print(f"[Migrated API keys] User: {user_id}")
