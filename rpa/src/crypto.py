"""
Password encryption utility using AES-256-CBC (Compatible with Dashboard Node.js).
Format: iv_hex:ciphertext_hex
"""
import os
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

def _get_encryption_key() -> bytes:
    """Derive a 32-byte key from ENCRYPTION_KEY using SHA-256."""
    key = os.environ.get("ENCRYPTION_KEY", "")
    if not key:
        raise ValueError("ENCRYPTION_KEY environment variable not set")
    return hashlib.sha256(key.encode()).digest()

def encrypt_password(plaintext: str) -> str:
    """Encrypt password → iv_hex:ciphertext_hex."""
    key = _get_encryption_key()
    iv = os.urandom(16)
    
    # Pad plaintext to 16 bytes (AES block size)
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext.encode()) + padder.finalize()
    
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    
    return f"{iv.hex()}:{ciphertext.hex()}"

def decrypt_password(ciphertext_str: str) -> str:
    """Decrypt password from iv_hex:ciphertext_hex."""
    key = _get_encryption_key()
    parts = ciphertext_str.split(":")
    if len(parts) < 2:
        raise ValueError("Invalid encrypted format (expected iv:ciphertext)")
    
    iv = bytes.fromhex(parts[0])
    ciphertext = bytes.fromhex(parts[1])
    
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(ciphertext) + decryptor.finalize()
    
    # Unpad data
    unpadder = padding.PKCS7(128).unpadder()
    data = unpadder.update(padded_data) + unpadder.finalize()
    
    return data.decode("utf-8")

