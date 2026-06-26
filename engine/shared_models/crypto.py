"""
engine/shared_models/crypto.py

Engine-side mirror of the backend's BYOK key encryption helpers.

The backend (authentication app) encrypts each organisation's API keys at rest
using Fernet, with the key derived from API_KEY_ENCRYPTION_SECRET via PBKDF2.
The engine is a *separate* Django project and cannot import the backend
`authentication` app, so it needs its own decrypt implementation that uses the
EXACT same derivation (same secret, salt, and iteration count). As long as
API_KEY_ENCRYPTION_SECRET matches in both projects, ciphertext written by the
backend decrypts cleanly here.
"""

import base64
import logging

from django.conf import settings
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# Must match backend/authentication/models.py::get_fernet exactly.
_SALT = b'llm-monitor-salt-123'
_ITERATIONS = 100000


def get_fernet():
    secret = getattr(settings, 'API_KEY_ENCRYPTION_SECRET', None) or settings.SECRET_KEY
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=_ITERATIONS,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return Fernet(key)


def decrypt_value(encrypted_value: str) -> str:
    """
    Decrypt a backend-encrypted API key.

    Returns "" on any failure (missing value, wrong secret, corrupt ciphertext)
    so callers fall back to the .env key instead of forwarding garbage —
    unlike the backend helper, we never return the ciphertext on error.
    """
    if not encrypted_value:
        return ""
    try:
        f = get_fernet()
        return f.decrypt(encrypted_value.encode()).decode()
    except Exception as e:
        logger.warning(f"BYOK decrypt failed; falling back to .env: {e}")
        return ""
