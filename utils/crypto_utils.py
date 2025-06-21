from cryptography.fernet import Fernet
import os

# === Fernet Setup ===
SECRET_KEY = os.getenv("SECRET_KEY")

print("🔐 [DEBUG] Loading SECRET_KEY from environment...")
if not SECRET_KEY:
    raise RuntimeError("❌ SECRET_KEY environment variable is not set!")

try:
    fernet = Fernet(SECRET_KEY.encode())
    print(f"✅ [DEBUG] Fernet initialized with key: {SECRET_KEY} (Length: {len(SECRET_KEY)})")
except Exception as e:
    raise ValueError(f"❌ Invalid SECRET_KEY format. Must be 32-byte base64: {e}")

# === Encryption Helpers ===
def encrypt_data(data: str) -> str:
    encrypted = fernet.encrypt(data.encode()).decode()
    print(f"🔐 [ENCRYPT] Plain: {data} → Encrypted: {encrypted}")
    return encrypted

def decrypt_data(data: str) -> str:
    decrypted = fernet.decrypt(data.encode()).decode()
    print(f"🔓 [DECRYPT] Encrypted: {data} → Decrypted: {decrypted}")
    return decrypted
