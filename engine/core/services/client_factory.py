"""
engine/core/services/client_factory.py

Centralized LLM client factory with in-memory instance caching.

Cache key: (provider, org_id, hash(api_key))
If the same org makes another prompt call with the same key, the existing
client instance is reused — no new SDK connection is created.

Supports: openai, gemini, perplexity, anthropic, xai, deepseek
"""

import logging
import hashlib
from typing import Any, Optional

from .api_key_service import get_org_settings, get_api_key, is_enabled, credential_provider

logger = logging.getLogger(__name__)

# In-memory client cache: (provider, org_id, key_hash) → client instance
_client_cache: dict = {}


def _key_hash(api_key: str) -> str:
    """Return a short hash of the API key for cache keying (never stores the raw key)."""
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]


def get_client(provider: str, org_id: Optional[int] = None) -> Any:
    """
    Return a cached (or freshly initialized) LLM client for the given provider.

    Args:
        provider: One of 'openai', 'gemini', 'perplexity', 'anthropic', 'xai', 'deepseek'
        org_id:   Organisation ID to resolve DB-level API keys. If None, uses .env only.

    Returns:
        An initialized SDK client object.

    Raises:
        Exception if the provider is disabled or no API key is configured.
    """
    org = get_org_settings(org_id) if org_id else None

    if not is_enabled(org, provider):
        raise Exception(f"Provider '{provider}' is disabled for org {org_id}")

    # Some providers (Claude) are transported over OpenRouter, so the credential
    # that authenticates the call belongs to a different provider slug than the
    # one the caller asked for.
    key_provider = credential_provider(provider)
    api_key = get_api_key(org, key_provider)
    if not api_key:
        raise Exception(
            f"No API key configured for provider '{provider}' "
            f"(credential '{key_provider}', org {org_id})"
        )

    cache_key = (provider, org_id, _key_hash(api_key))
    if cache_key in _client_cache:
        return _client_cache[cache_key]

    client = _build_client(provider, api_key)
    _client_cache[cache_key] = client
    logger.debug(f"ClientFactory: initialized new client for provider='{provider}' org={org_id}")
    return client


def _build_client(provider: str, api_key: str) -> Any:
    """Instantiate a new SDK client for the given provider and API key."""
    if provider == 'openai':
        from openai import OpenAI
        return OpenAI(api_key=api_key, timeout=60)

    elif provider == 'gemini':
        # Return a config dict; Gemini is invoked via REST/genai SDK
        return {'api_key': api_key, 'timeout': 60}

    elif provider == 'perplexity':
        # Perplexity uses OpenAI-compatible client with custom base_url
        from openai import OpenAI
        return OpenAI(
            api_key=api_key,
            base_url='https://api.perplexity.ai',
            timeout=60,
        )

    elif provider == 'anthropic':
        # Claude is served through OpenRouter's OpenAI-compatible endpoint. The
        # adapter keeps the Anthropic `messages.create` surface so every existing
        # Claude call site works unchanged.
        from django.conf import settings
        from .openrouter_client import OpenRouterAnthropicClient
        return OpenRouterAnthropicClient(
            api_key=api_key,
            model=getattr(settings, 'ANTHROPIC_MODEL', 'anthropic/claude-sonnet-5'),
            base_url=getattr(settings, 'OPENROUTER_BASE_URL', None),
            timeout=60,
            site_url=getattr(settings, 'OPENROUTER_SITE_URL', None),
            site_title=getattr(settings, 'OPENROUTER_SITE_TITLE', None),
        )

    elif provider == 'xai':
        from openai import OpenAI
        return OpenAI(
            api_key=api_key,
            base_url='https://api.x.ai/v1',
            timeout=60,
        )

    elif provider == 'deepseek':
        from openai import OpenAI
        return OpenAI(
            api_key=api_key,
            base_url='https://api.deepseek.com/v1',
            timeout=60,
        )

    else:
        raise ValueError(f"ClientFactory: unknown provider '{provider}'")


def invalidate_org_clients(org_id: int) -> None:
    """
    Remove all cached clients for a given organisation.
    Call this when the organisation's API keys are updated or deleted.
    """
    keys_to_remove = [k for k in _client_cache if k[1] == org_id]
    for k in keys_to_remove:
        del _client_cache[k]
    if keys_to_remove:
        logger.info(f"ClientFactory: invalidated {len(keys_to_remove)} cached clients for org {org_id}")
