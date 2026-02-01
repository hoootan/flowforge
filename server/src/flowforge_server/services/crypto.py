"""Cryptographic utilities for secure credential storage.

Uses Fernet (AES-128-CBC) symmetric encryption with key derivation via PBKDF2.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from functools import lru_cache
from typing import TYPE_CHECKING

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

if TYPE_CHECKING:
    pass


class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""

    pass


class EncryptionKeyMissing(EncryptionError):
    """Raised when the encryption key is not configured."""

    pass


def _get_salt() -> bytes:
    """
    Get the encryption salt from configuration.

    Returns:
        Salt bytes for PBKDF2 key derivation.

    Raises:
        EncryptionError: If salt is not configured in production.
    """
    from flowforge_server.config import get_settings

    settings = get_settings()

    if settings.encryption_salt:
        # Use configured salt (recommended for production)
        return settings.encryption_salt.encode()

    # In development, use a default salt with a warning
    if settings.is_development:
        import warnings

        warnings.warn(
            "FLOWFORGE_ENCRYPTION_SALT is not set. Using default salt for development. "
            "This is insecure for production - set a unique salt per installation.",
            UserWarning,
            stacklevel=3,
        )
        return b"flowforge_dev_salt_not_for_production"

    # In production, require explicit salt configuration
    raise EncryptionError(
        "FLOWFORGE_ENCRYPTION_SALT must be set in production. "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(16))\""
    )


def _derive_key(master_key: str, salt: bytes | None = None) -> bytes:
    """
    Derive a Fernet-compatible key from a master key using PBKDF2.

    Args:
        master_key: The master encryption key (from env var)
        salt: Salt for key derivation. If None, uses configured salt.

    Returns:
        32-byte key suitable for Fernet (base64 encoded to 44 bytes)
    """
    if salt is None:
        salt = _get_salt()

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,  # OWASP recommended minimum for PBKDF2-SHA256
        backend=default_backend(),
    )
    key = kdf.derive(master_key.encode())
    return base64.urlsafe_b64encode(key)


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    """
    Get a cached Fernet instance.

    The encryption key is derived from FLOWFORGE_ENCRYPTION_KEY environment variable.
    """
    from flowforge_server.config import get_settings

    settings = get_settings()

    if not settings.encryption_key:
        raise EncryptionKeyMissing(
            "FLOWFORGE_ENCRYPTION_KEY environment variable is not set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    derived_key = _derive_key(settings.encryption_key)
    return Fernet(derived_key)


def encrypt_value(plaintext: str) -> str:
    """
    Encrypt a plaintext value.

    Args:
        plaintext: The value to encrypt (e.g., an API key)

    Returns:
        Base64-encoded encrypted value

    Raises:
        EncryptionKeyMissing: If the encryption key is not configured
        EncryptionError: If encryption fails
    """
    if not plaintext:
        return ""

    try:
        fernet = _get_fernet()
        encrypted = fernet.encrypt(plaintext.encode())
        return encrypted.decode()
    except EncryptionKeyMissing:
        raise
    except Exception as e:
        raise EncryptionError(f"Failed to encrypt value: {e}") from e


def decrypt_value(ciphertext: str) -> str:
    """
    Decrypt an encrypted value.

    Args:
        ciphertext: Base64-encoded encrypted value

    Returns:
        Decrypted plaintext

    Raises:
        EncryptionKeyMissing: If the encryption key is not configured
        EncryptionError: If decryption fails (wrong key, corrupted data, etc.)
    """
    if not ciphertext:
        return ""

    try:
        fernet = _get_fernet()
        decrypted = fernet.decrypt(ciphertext.encode())
        return decrypted.decode()
    except EncryptionKeyMissing:
        raise
    except InvalidToken:
        raise EncryptionError(
            "Failed to decrypt value. The encryption key may have changed or the data is corrupted."
        )
    except Exception as e:
        raise EncryptionError(f"Failed to decrypt value: {e}") from e


def rotate_encryption(
    old_ciphertext: str,
    old_key: str,
    new_key: str,
) -> str:
    """
    Re-encrypt a value with a new encryption key.

    This is used during key rotation to update all stored encrypted values.

    Args:
        old_ciphertext: Value encrypted with the old key
        old_key: The old master encryption key
        new_key: The new master encryption key

    Returns:
        Value encrypted with the new key

    Raises:
        EncryptionError: If re-encryption fails
    """
    if not old_ciphertext:
        return ""

    try:
        # Decrypt with old key
        old_derived = _derive_key(old_key)
        old_fernet = Fernet(old_derived)
        plaintext = old_fernet.decrypt(old_ciphertext.encode()).decode()

        # Encrypt with new key
        new_derived = _derive_key(new_key)
        new_fernet = Fernet(new_derived)
        new_ciphertext = new_fernet.encrypt(plaintext.encode())

        return new_ciphertext.decode()
    except InvalidToken:
        raise EncryptionError(
            "Failed to decrypt with old key. The key may be incorrect."
        )
    except Exception as e:
        raise EncryptionError(f"Failed to rotate encryption: {e}") from e


def generate_encryption_key() -> str:
    """
    Generate a new encryption key suitable for FLOWFORGE_ENCRYPTION_KEY.

    Returns:
        A secure random key (URL-safe base64, 32 bytes)
    """
    return secrets.token_urlsafe(32)


def get_key_prefix(api_key: str, length: int = 8) -> str:
    """
    Get a display-safe prefix of an API key.

    Args:
        api_key: The full API key
        length: Number of characters to include in prefix

    Returns:
        The first `length` characters followed by "..."
    """
    if not api_key:
        return ""
    if len(api_key) <= length:
        return api_key
    return api_key[:length] + "..."


def hash_for_comparison(value: str) -> str:
    """
    Create a hash of a value for comparison purposes.

    This is NOT for encryption - use for duplicate detection, etc.

    Args:
        value: The value to hash

    Returns:
        SHA-256 hash as hex string
    """
    return hashlib.sha256(value.encode()).hexdigest()


def clear_cache() -> None:
    """Clear the cached Fernet instance. Used for testing or key rotation."""
    _get_fernet.cache_clear()
