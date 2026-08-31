"""Token-consumption recording, shared by every LLM call site.

One place that knows how to read a provider's usage block and write a row, so
instrumenting a new call site is a single import rather than a copy of the
parsing.

Two providers report differently and the difference matters:

* **OpenRouter** returns ``usage`` with token counts AND a real ``cost`` in USD,
  plus ``is_byok`` saying whose key paid.
* **Google Gemini** returns ``usageMetadata`` with token counts and **no price
  at all** — it bills against a request quota instead. Its ``cost`` is stored as
  NULL, which means "unknown", never "free". A dashboard that shows 0 there
  would be lying about the tightest constraint in the system.

Every function here is best-effort and never raises: a failure to record usage
must not fail the request that produced it.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# model_name is varchar(50) on the table. Slugs fit today (the longest in use is
# ~36 chars) but truncate rather than let a future one raise a DataError — the
# column is deliberately not widened, since an AlterField on this table is what
# produced the varchar(50) defect that broke content generation.
MODEL_NAME_MAX = 50

PROVIDER_OPENROUTER = 'openrouter'
PROVIDER_GEMINI = 'gemini'
PROVIDER_OTHER = 'other'


def provider_for_model(model_name: str) -> str:
    """Which credential paid, inferred from the model slug.

    OpenRouter slugs always carry a vendor prefix ("openai/gpt-5-mini"). A bare
    name like "gemini-flash-latest" is Google's own API, reached with the
    GEMINI_API_KEY rather than through OpenRouter.
    """
    name = (model_name or '').strip()
    if not name:
        return PROVIDER_OTHER
    if '/' in name:
        return PROVIDER_OPENROUTER
    if name.lower().startswith('gemini'):
        return PROVIDER_GEMINI
    return PROVIDER_OTHER


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _to_decimal(value: Any) -> Optional[Decimal]:
    """USD cost as Decimal, or None when the provider reports none.

    None and 0 are different answers: Gemini reports no cost (None = unknown),
    while a free OpenRouter model genuinely costs 0.
    """
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def parse_openrouter_usage(response: Any) -> Dict[str, Any]:
    """Read an OpenRouter chat-completion response into recordable fields.

    Accepts the raw dict from ``requests``/``httpx`` or an SDK object, since
    call sites in this codebase use both.
    """
    if response is None:
        return {}

    if isinstance(response, dict):
        usage = response.get('usage') or {}
        model = response.get('model') or ''
    else:
        usage = getattr(response, 'usage', None) or {}
        model = getattr(response, 'model', '') or ''
        if not isinstance(usage, dict):
            usage = {
                'prompt_tokens': getattr(usage, 'prompt_tokens', 0),
                'completion_tokens': getattr(usage, 'completion_tokens', 0),
                'total_tokens': getattr(usage, 'total_tokens', 0),
                'cost': getattr(usage, 'cost', None),
                'is_byok': getattr(usage, 'is_byok', False),
            }

    details = usage.get('prompt_tokens_details') or {}
    cached = _to_int(details.get('cached_tokens')) if isinstance(details, dict) else 0

    return {
        'model_name': str(model)[:MODEL_NAME_MAX],
        'provider': PROVIDER_OPENROUTER,
        'input_tokens': _to_int(usage.get('prompt_tokens')),
        'output_tokens': _to_int(usage.get('completion_tokens')),
        'cached_tokens': cached,
        'cost': _to_decimal(usage.get('cost')),
        'is_byok': bool(usage.get('is_byok')),
    }


def parse_gemini_usage(response: Any, model_name: str = '') -> Dict[str, Any]:
    """Read a Google Gemini response into recordable fields.

    Handles both shapes the codebase produces: the SDK object's
    ``usage_metadata`` and the REST body's ``usageMetadata``. Cost is always
    None — Google does not report one.
    """
    if response is None:
        return {}

    meta: Any = None
    if isinstance(response, dict):
        meta = response.get('usageMetadata') or response.get('usage_metadata')
    else:
        meta = getattr(response, 'usage_metadata', None)

    def field(*names: str) -> int:
        for n in names:
            if isinstance(meta, dict):
                if n in meta:
                    return _to_int(meta[n])
            elif meta is not None and hasattr(meta, n):
                return _to_int(getattr(meta, n))
        return 0

    return {
        'model_name': str(model_name or 'gemini')[:MODEL_NAME_MAX],
        'provider': PROVIDER_GEMINI,
        'input_tokens': field('prompt_token_count', 'promptTokenCount'),
        'output_tokens': field('candidates_token_count', 'candidatesTokenCount'),
        'cached_tokens': field('cached_content_token_count', 'cachedContentTokenCount'),
        # Google reports no price. NULL means unknown, not free.
        'cost': None,
        'is_byok': False,
    }


def record_usage(
    org_id: Optional[int],
    user: Any,
    feature: str,
    *,
    model_name: str = '',
    provider: str = '',
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_tokens: int = 0,
    cost: Any = None,
    is_byok: bool = False,
    status_value: str = 'success',
    error_message: Any = None,
) -> None:
    """Write one usage row. Best-effort — never raises, never blocks a request."""
    if not org_id:
        return
    try:
        from .models import ContentGenerationUsage

        in_tok = _to_int(input_tokens)
        out_tok = _to_int(output_tokens)
        resolved_provider = provider or provider_for_model(model_name)

        ContentGenerationUsage.objects.create(
            organisation_id=org_id,
            user=user if (user is not None and getattr(user, 'is_authenticated', False)) else None,
            feature=str(feature or 'unknown')[:50],
            model_name=str(model_name or 'unknown')[:MODEL_NAME_MAX],
            provider=resolved_provider,
            input_tokens=in_tok,
            output_tokens=out_tok,
            total_tokens=in_tok + out_tok,
            cached_tokens=_to_int(cached_tokens),
            cost=_to_decimal(cost),
            is_byok=bool(is_byok),
            status=status_value,
            error_message=(str(error_message)[:2000] if error_message else None),
        )
    except Exception as exc:  # noqa: BLE001
        # Recording is observability, not the job. Swallow and move on.
        logger.warning('Failed to record token usage for %s: %s', feature, exc)


def record_openrouter_call(org_id, user, feature: str, response: Any, **overrides) -> None:
    """Convenience: parse an OpenRouter response and record it in one call."""
    fields = parse_openrouter_usage(response)
    if not fields:
        return
    fields.update(overrides)
    record_usage(org_id, user, feature, **fields)


def record_gemini_call(org_id, user, feature: str, response: Any, model_name: str = '', **overrides) -> None:
    """Convenience: parse a Gemini response and record it in one call."""
    fields = parse_gemini_usage(response, model_name=model_name)
    if not fields:
        return
    fields.update(overrides)
    record_usage(org_id, user, feature, **fields)
