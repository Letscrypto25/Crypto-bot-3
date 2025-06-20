import firebase_admin
from firebase_admin import credentials, db
from encryption import decrypt_data
import requests
import base64

# 🔐 Load your Firebase credentials
cred = credentials.Certificate("FIREBASE_CREDENTIALS_ENCODED")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://crypto-bot-3-default-rtdb.firebaseio.com"
})

def test_luno_balance(user_id: str):
    print(f"🔍 Verifying Luno credentials for user: {user_id}")
    ref = db.reference(f"users/{user_id}")
    data = ref.get()

    if not data:
        print("❌ User not found in database.")
        return

    enc_key = data.get("luno_api_key")
    enc_secret = data.get("luno_api_secret")

    if not enc_key or not enc_secret:
        print("❌ Missing encrypted Luno API keys in Firebase.")
        return

    # 🔓 Decrypt the credentials
    api_key = decrypt_data(enc_key)
    api_secret = decrypt_data(enc_secret)

    if not api_key or not api_secret:
        print("❌ Failed to decrypt Luno credentials.")
        return

    print(f"✅ Decrypted API Key: {api_key[:6]}... (len={len(api_key)})")
    print(f"✅ Decrypted Secret: {api_secret[:6]}... (len={len(api_secret)})")

    # 🔁 Test the API call to Luno
    try:
        auth_string = f"{api_key}:{api_secret}".encode()
        auth = base64.b64encode(auth_string).decode()
        headers = {"Authorization": f"Basic {auth}"}

        response = requests.get("https://api.luno.com/api/1/balance", headers=headers)
        response.raise_for_status()

        balances = response.json().get("balance", [])
        if not balances:
            print("⚠️ No balances returned, but credentials work.")
        else:
            print("✅ Successfully fetched Luno balances:")
            for asset in balances:
                print(f"• {asset['asset']}: {asset['balance']}")

    except Exception as e:
        print("❌ Error fetching balance from Luno:", e)

if __name__ == "__main__":
    test_luno_balance("7521070576")
