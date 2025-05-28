import base64
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import bcrypt

load_dotenv()

# === Symmetric Encryption Key ===
# Generate one with: Fernet.generate_key().decode()
SECRET_KEY = os.getenv("SECRET_KEY")

if not FERNET_KEY:
    raise ValueError("Missing SECRET_KEY in environment variables.")

fernet = Fernet(SECRET_KEY.encode())

# === Encryption Utilities ===
def encrypt_data(data: str) -> str:
    return fernet.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    return fernet.decrypt(encrypted_data.encode()).decode()

# === Password Hashing ===
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())
