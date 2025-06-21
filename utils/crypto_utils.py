from cryptography.fernet import Fernet
import os

# === Fernet Setup ===
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set!")

try:
    fernet = Fernet(SECRET_KEY.encode())
except Exception as e:
    raise ValueError(f"Invalid SECRET_KEY format. Must be 32-byte base64: {e}")

# === Encryption Helpers ===
def encrypt_data(data: str) -> str:
    return fernet.encrypt(data.encode()).decode()

def decrypt_data(data: str) -> str:
    return fernet.decrypt(data.encode()).decode()
