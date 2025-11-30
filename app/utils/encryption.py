# File: app/utils/encryption.py
"""
/app/utils/encryption.py
Token encryption utilities for secure storage at rest
"""

import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

logger = logging.getLogger(__name__)

# Module-level cipher instance (initialized on first use)
_cipher: Optional[Fernet] = None


def _get_cipher() -> Fernet:
    """Get or initialize the Fernet cipher"""
    global _cipher
    if _cipher is None:
        key = current_app.config.get("ENCRYPTION_KEY")
        if not key:
            raise ValueError("ENCRYPTION_KEY not configured")
        # Ensure key is bytes
        if isinstance(key, str):
            key = key.encode()
        _cipher = Fernet(key)
    return _cipher


def encrypt_token(plain_text: Optional[str]) -> Optional[str]:
    """
    Encrypt a token for secure storage.

    Args:
        plain_text: The plain text token to encrypt

    Returns:
        Base64-encoded encrypted string, or None if input is None
    """
    if plain_text is None:
        return None

    try:
        cipher = _get_cipher()
        encrypted = cipher.encrypt(plain_text.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Error encrypting token: {str(e)}")
        raise


def decrypt_token(encrypted_text: Optional[str]) -> Optional[str]:
    """
    Decrypt a stored token.

    Args:
        encrypted_text: The encrypted token string

    Returns:
        Decrypted plain text, or None if input is None
    """
    if encrypted_text is None:
        return None

    try:
        cipher = _get_cipher()
        decrypted = cipher.decrypt(encrypted_text.encode())
        return decrypted.decode()
    except InvalidToken:
        # Token might be stored in plain text (migration scenario)
        logger.warning("Failed to decrypt token - may be plain text (pre-encryption)")
        return encrypted_text
    except Exception as e:
        logger.error(f"Error decrypting token: {str(e)}")
        raise


def is_encrypted(text: str) -> bool:
    """
    Check if a string appears to be Fernet-encrypted.
    Fernet tokens are base64-encoded and start with 'gAAAAA'
    """
    if not text:
        return False
    return text.startswith("gAAAAA")


def reset_cipher():
    """Reset the cipher instance (useful for testing)"""
    global _cipher
    _cipher = None
