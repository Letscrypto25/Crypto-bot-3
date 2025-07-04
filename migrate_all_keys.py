import firebase_admin
from firebase_admin import credentials, db
from encryption import encrypt_data  # Only needed if keys should be encrypted

# Load credentials
cred = credentials.Certificate("FIREBASE_CREDENTIALS_ENCODED")

# Initialize Firebase (✅ fix the DB URL here)
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://crypto-bot-3-default-rtdb.firebaseio.com"
})

def migrate_user_keys():
    ref = db.reference("users")
    users = ref.get()

    if not users:
        print("No users found.")
        return

    migrated = {"luno": 0, "binance": 0, "skipped": 0}

    for user_id, data in users.items():
        api_key = data.get("api_key")
        api_secret = data.get("api_secret")

        user_ref = ref.child(user_id)

        needs_luno = not data.get("luno_api_key") or not data.get("luno_api_secret")
        needs_binance = not data.get("binance_api_key") or not data.get("binance_api_secret")

        if api_key and api_secret:
            updates = {}

            if needs_luno:
                updates["luno_api_key"] = encrypt_data(api_key)
                updates["luno_api_secret"] = encrypt_data(api_secret)
                migrated["luno"] += 1

            if needs_binance:
                updates["binance_api_key"] = encrypt_data(api_key)
                updates["binance_api_secret"] = encrypt_data(api_secret)
                migrated["binance"] += 1

            if updates:
                user_ref.update(updates)
                print(f"Migrated for user {user_id}: {list(updates.keys())}")
            else:
                migrated["skipped"] += 1
                print(f"No migration needed for user {user_id} (already has both sets).")
        else:
            migrated["skipped"] += 1
            print(f"Skipping user {user_id} (no base API keys found).")

    print("\n✅ Migration Complete:")
    print(f"🔐 Luno keys migrated: {migrated['luno']}")
    print(f"🔐 Binance keys migrated: {migrated['binance']}")
    print(f"⏭️ Users skipped: {migrated['skipped']}")

if __name__ == "__main__":
    migrate_user_keys()
