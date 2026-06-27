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

# Map provider slug → Django settings attribute name (.env fallback key)
ENV_KEY_MAP = {
    'openai':     'OPENAI_API_KEY',
    'gemini':     'GEMINI_API_KEY',
    'perplexity': 'PERPLEXITY_API_KEY',
    'anthropic':  'ANTHROPIC_API_KEY',
    'xai':        'XAI_API_KEY',
    'deepseek':   'DEEPSEEK_API_KEY',
}


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
            try:
                # Decrypt using the engine-local helper (the backend
                # `authentication` app is not importable here). Returns "" on
                # failure so we fall through to the .env key below.
                from shared_models.crypto import decrypt_value
                raw = decrypt_value(encrypted)
                if raw:
                    return raw
            except Exception as e:
                logger.warning(f"APIKeyService: decrypt failed for {provider}: {e}")

    # .env fallback
    env_attr = ENV_KEY_MAP.get(provider)
    if env_attr:
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
