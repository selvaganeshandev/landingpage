"""
engine/core/services/api_key_service.py

Centralized service for retrieving organization API keys and provider settings.
Applies a two-level lookup:
  1. Organisation database record (encrypted, per-org BYOK)
  2. System .env fallback (settings.py values)

Results are cached in Redis for 5 minutes (TTL = 300s).
Cache is invalidated immediately when organization settings are updated via the API.
"""

import logging
from typing import Optional
from django.core.cache import cache
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutes

# Map provider slug → candidate Django settings attribute name(s) for the
# .env fallback. Multiple names are tried in order so the same service works
# across the backend and engine processes, which historically named the same
# Gemini key differently (backend: GOOGLE_GEMINI_API_KEY, engine: GEMINI_API_KEY).
ENV_KEY_MAP = {
    'openai':     ('OPENAI_API_KEY',),
    'gemini':     ('GEMINI_API_KEY', 'GOOGLE_GEMINI_API_KEY'),
    'perplexity': ('PERPLEXITY_API_KEY',),
    'anthropic':  ('ANTHROPIC_API_KEY', 'CLAUDE_API_KEY'),
    'openrouter': ('OPENROUTER_API_KEY',),
    'xai':        ('XAI_API_KEY',),
    'deepseek':   ('DEEPSEEK_API_KEY',),
}

# Providers whose calls are transported over OpenRouter rather than the vendor's
# own API. The provider slug is unchanged everywhere else (org.anthropic_enabled,
# org.perplexity_enabled, the "Claude"/"Perplexity" platform labels, tracked
# rows) — only the credential and the wire format differ, so historical data
# stays comparable.
#
# Perplexity joined this set after the direct api.perplexity.ai key ran out of
# credit and every Perplexity call died on a 401 insufficient_quota, silently
# zeroing that platform's tracking. Routing it through OpenRouter puts it on the
# same single balance as Claude and the internal model, so one top-up covers all
# of them. `perplexity/sonar` on OpenRouter is the same Sonar model with the same
# built-in web search — only the billing path changes.
OPENROUTER_ROUTED = {'anthropic', 'perplexity'}


def credential_provider(provider: str) -> str:
    """Return the provider slug whose API key actually authenticates ``provider``."""
    return 'openrouter' if provider in OPENROUTER_ROUTED else provider


def _decrypt_byok(encrypted: str) -> Optional[str]:
    """Decrypt a per-org BYOK ciphertext regardless of which process we run in.

    The engine exposes ``shared_models.crypto`` and the backend exposes
    ``authentication.models.decrypt_value``; only one is importable in a given
    process. Both derive the SAME Fernet key from ``API_KEY_ENCRYPTION_SECRET``
    (salt ``llm-monitor-salt-123``, 100k PBKDF2 iterations), so whichever is
    available yields identical plaintext. If neither module is importable we
    derive the key inline as a guaranteed, process-agnostic last resort — this
    is what makes BYOK resolve in the backend, where ``shared_models`` has no
    ``crypto`` submodule and the old import silently fell through to ``.env``.

    Returns None on any failure so the caller falls back to the ``.env`` key
    instead of forwarding garbage. The backend helper returns the ciphertext
    unchanged on failure, so a result equal to the input is treated as failure.
    """
    for module_path in ('shared_models.crypto', 'authentication.models'):
        try:
            from importlib import import_module
            decrypt = getattr(import_module(module_path), 'decrypt_value')
            value = decrypt(encrypted)
            if value and value != encrypted:
                return value
        except Exception:
            continue

    # Inline derivation — matches backend/authentication and engine/shared_models.
    try:
        import base64
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        secret = getattr(django_settings, 'API_KEY_ENCRYPTION_SECRET', None) or django_settings.SECRET_KEY
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                         salt=b'llm-monitor-salt-123', iterations=100000)
        key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
        return Fernet(key).decrypt(encrypted.encode()).decode()
    except Exception as e:
        logger.warning(f"APIKeyService: BYOK decrypt failed: {e}")
        return None


def get_org_settings(org_id: int):
    """
    Return the Organisation object for the given org_id, using Redis cache.
    Cache key: org_{org_id}_settings
    TTL: 300 seconds (5 minutes)
    """
    cache_key = f'org_{org_id}_settings'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        from shared_models.models import Organisation
        org = Organisation.objects.get(id=org_id)
    except Exception:
        try:
            # Fallback: try authentication.Organisation (backend model)
            from authentication.models import Organisation
            org = Organisation.objects.get(id=org_id)
        except Exception as e:
            logger.warning(f"APIKeyService: Could not load org {org_id}: {e}")
            return None

    cache.set(cache_key, org, CACHE_TTL)
    return org


def get_api_key(org, provider: str) -> Optional[str]:
    """
    Return the decrypted API key for the given provider.

    Priority:
      1. Organisation.{provider}_api_key (database, encrypted)
      2. settings.{PROVIDER}_API_KEY (.env fallback)

    Returns None if neither is configured.
    """
    if org is not None:
        encrypted = getattr(org, f'{provider}_api_key', None)
        if encrypted:
            # Process-agnostic decrypt: works in both the backend and engine.
            raw = _decrypt_byok(encrypted)
            if raw:
                return raw

    # .env fallback: try each candidate settings attribute in order.
    for env_attr in ENV_KEY_MAP.get(provider, ()):
        fallback = getattr(django_settings, env_attr, None)
        if fallback:
            return fallback

    return None


def is_enabled(org, provider: str) -> bool:
    """
    Return True if the provider is enabled for the given organisation.
    Defaults to True if the field does not exist (backwards compatibility).
    """
    if org is None:
        return True  # no org context → allow fallback
    return getattr(org, f'{provider}_enabled', True)
