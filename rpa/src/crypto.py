"""
Password encryption utility using AES-256 (Fernet).
"""
import os
from cryptography.fernet import Fernet
import base64
import hashlib


def _get_fernet() -> Fernet:
    """Get Fernet cipher from ENCRYPTION_KEY env var."""
    key = os.environ.get("ENCRYPTION_KEY", "")
    if not key:
        raise ValueError("ENCRYPTION_KEY environment variable not set")
    # Derive a 32-byte key from the hex string
    derived = hashlib.sha256(key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(derived)
    return Fernet(fernet_key)


def encrypt_password(plaintext: str) -> str:
    """Encrypt password → base64 encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_password(ciphertext: str) -> str:
    """Decrypt password from base64 encoded ciphertext."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
