from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
import hashlib
import os

# Key for AES encryption (must be 16, 24, or 32 bytes)
AES_SECRET = os.getenv("ENCRYPTION_KEY", "default_key_32_byte__").encode()[:32]

def encrypt_data(data: str) -> str:
    cipher = AES.new(AES_SECRET, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(data.encode(), AES.block_size))
    iv = base64.b64encode(cipher.iv).decode()
    ct = base64.b64encode(ct_bytes).decode()
    return f"{iv}:{ct}"

def decrypt_data(encrypted: str) -> str:
    iv, ct = encrypted.split(":")
    iv = base64.b64decode(iv)
    ct = base64.b64decode(ct)
    cipher = AES.new(AES_SECRET, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ct), AES.block_size).decode()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()
