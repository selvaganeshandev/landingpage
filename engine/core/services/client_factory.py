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

    # Some providers (Claude, Perplexity) are transported over OpenRouter, so the
    # credential that authenticates the call belongs to a different provider slug
    # than the one the caller asked for.
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


def _openrouter_headers() -> Optional[dict]:
    """Optional OpenRouter attribution headers, matching OpenRouterAnthropicClient.

    Returns None (not an empty dict) when neither is configured, so the SDK is
    given no ``default_headers`` at all rather than an empty mapping.
    """
    from django.conf import settings
    headers = {}
    site_url = getattr(settings, 'OPENROUTER_SITE_URL', None)
    site_title = getattr(settings, 'OPENROUTER_SITE_TITLE', None)
    if site_url:
        headers['HTTP-Referer'] = site_url
    if site_title:
        headers['X-Title'] = site_title
    return headers or None


def _build_client(provider: str, api_key: str) -> Any:
    """Instantiate a new SDK client for the given provider and API key."""
    if provider == 'openai':
        # ChatGPT is served through OpenRouter, same as Claude and Perplexity, so
        # every LLM call in the platform bills one balance. OpenRouter speaks both
        # SDK surfaces this provider uses — chat.completions AND /responses with
        # the web_search tool — so process_prompt_with_chatgpt is unchanged; only
        # the model slug gains its `openai/` prefix (see OPENAI_CHATGPT_MODEL).
        from django.conf import settings
        from openai import OpenAI
        return OpenAI(
            api_key=api_key,
            base_url=getattr(settings, 'OPENROUTER_BASE_URL', None) or 'https://openrouter.ai/api/v1',
            timeout=60,
            default_headers=_openrouter_headers(),
        )

    elif provider == 'gemini':
        # Return a config dict; Gemini is invoked via REST/genai SDK
        return {'api_key': api_key, 'timeout': 60}

    elif provider == 'perplexity':
        # Perplexity is served through OpenRouter, not api.perplexity.ai. Both
        # speak the OpenAI chat-completions wire format, so only the base_url,
        # the credential (OPENROUTER_API_KEY) and the model slug
        # (`perplexity/sonar` instead of `sonar`) change — every call site is
        # unchanged. See OPENROUTER_ROUTED in api_key_service.py for why.
        from django.conf import settings
        from openai import OpenAI
        return OpenAI(
            api_key=api_key,
            base_url=getattr(settings, 'OPENROUTER_BASE_URL', None) or 'https://openrouter.ai/api/v1',
            timeout=60,
            default_headers=_openrouter_headers(),
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

    elif provider == 'openrouter':
        # Generic OpenRouter client for INTERNAL (non-measured) work. Kept as its
        # own provider rather than repointing 'openai', because the tracked
        # ChatGPT call shares that client and must keep hitting OpenAI directly.
        from django.conf import settings
        from openai import OpenAI
        return OpenAI(
            api_key=api_key,
            base_url=getattr(settings, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
            timeout=60,
        )

    else:
        raise ValueError(f"ClientFactory: unknown provider '{provider}'")


def get_internal_client(org_id: Optional[int] = None) -> Any:
    """Client for INTERNAL, non-measured LLM work (topics, prompt generation,
    insights, chat, misinformation comparison).

    Always OpenRouter — as is ``get_client('openai')`` now. The two remain
    separate because they differ in MODEL, not transport: this one runs the cheap
    ``OPENROUTER_INTERNAL_MODEL``, while the tracked ChatGPT call keeps the
    flagship ``OPENAI_CHATGPT_MODEL`` so the measurement still reflects what a
    real ChatGPT user is told.

    Pair with ``settings.OPENROUTER_INTERNAL_MODEL`` for the model slug.
    """
    return get_client('openrouter', org_id=org_id)


def invalidate_org_clients(org_id: int) -> None:
    """
    Remove all cached clients for a given organisation.
    Call this when the organisation's API keys are updated or deleted.
    """
    keys_to_remove = [k for k in _client_cache if k[1] == org_id]
    for k in keys_to_remove:
        # pop() not del: the worker runs a threads pool, so another thread can
        # invalidate the same org between building this list and deleting from
        # it. A missing key is the outcome we wanted anyway.
        _client_cache.pop(k, None)
    if keys_to_remove:
        logger.info(f"ClientFactory: invalidated {len(keys_to_remove)} cached clients for org {org_id}")
