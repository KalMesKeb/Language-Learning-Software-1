# encryption.py
import os
from cryptography.fernet import Fernet

KEY_FILE = "enc_key.key"

def ensure_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        os.chmod(KEY_FILE, 0o600)
    else:
        with open(KEY_FILE, "rb") as f:
            key = f.read()
    return key

_key = ensure_key()
cipher = Fernet(_key)

def encrypt_bytes(data: bytes) -> bytes:
    return cipher.encrypt(data)

def decrypt_bytes(token: bytes) -> bytes:
    return cipher.decrypt(token)

def encrypt_str(s: str) -> bytes:
    return encrypt_bytes(s.encode("utf-8"))

def decrypt_str(token: bytes) -> str:
    return decrypt_bytes(token).decode("utf-8")
