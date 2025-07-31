"""
Encryption utilities for sensitive data.
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from backend.config.env import get_env_variable


def get_encryption_key():
    """
    Get or generate an encryption key for sensitive data.
    
    This uses a key derivation function with the JWT_SECRET as input
    to ensure the encryption key is tied to the application's secret.
    
    Returns:
        bytes: Encryption key
    """
    # Use JWT_SECRET as the base for our encryption key
    jwt_secret = get_env_variable('JWT_SECRET', '')
    if not jwt_secret:
        raise ValueError("JWT_SECRET environment variable is required for encryption")
    
    # Create a salt (this could be stored in the environment or a config file)
    # Using a fixed salt for simplicity, but in production, consider storing this separately
    salt = b'personal_ai_assistant_salt'
    
    # Use PBKDF2 to derive a key from our JWT secret
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(jwt_secret.encode()))
    return key


def encrypt_text(text):
    """
    Encrypt text using Fernet symmetric encryption.
    
    Args:
        text (str): Plain text to encrypt
        
    Returns:
        str: Encrypted text (base64-encoded)
    """
    if not text:
        return None
        
    key = get_encryption_key()
    f = Fernet(key)
    encrypted_data = f.encrypt(text.encode())
    return encrypted_data.decode()


def decrypt_text(encrypted_text):
    """
    Decrypt text that was encrypted with Fernet.
    
    Args:
        encrypted_text (str): Encrypted text (base64-encoded)
        
    Returns:
        str: Decrypted plain text
    """
    if not encrypted_text:
        return None
        
    key = get_encryption_key()
    f = Fernet(key)
    decrypted_data = f.decrypt(encrypted_text.encode())
    return decrypted_data.decode()
