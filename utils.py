# utils.py
import hashlib
import html
from typing import List

def hash_password(password: str) -> str:
    # simple salted hash (for demo). For production, use bcrypt/scrypt.
    salt = "nl_secure_salt_v1"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

def escape(s: str) -> str:
    return html.escape(s)

def split_words(sentence: str) -> List[str]:
    # naive split by spaces/punctuation for alignment display
    import re
    words = re.findall(r"\w+['’]?\w*|\S", sentence)
    return words
