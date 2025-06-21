import base64
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import bcrypt

load_dotenv()

# === Symmetric Encryption Key ===
# Generate one with: Fernet.generate_key().decode()
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("Missing SECRET_KEY in environment variables.")

try:
    fernet = Fernet(SECRET_KEY.encode())
except Exception as e:
    raise ValueError(f"Invalid SECRET_KEY format. Must be base64-encoded 32 bytes: {e}")

# === Encryption Utilities ===
def encrypt_data(data: str) -> str:
    encrypted = fernet.encrypt(data.encode()).decode()
    print(f"[DEBUG ENCRYPT] Raw: {data} → Encrypted: {encrypted}")
    return encrypted

def decrypt_data(encrypted_data: str) -> str:
    print(f"[DEBUG DECRYPT] Attempting to decrypt: {encrypted_data}")
    decrypted = fernet.decrypt(encrypted_data.encode()).decode()
    print(f"[DEBUG DECRYPT] Decrypted: {decrypted}")
    return decrypted

# === Password Hashing ===
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())
