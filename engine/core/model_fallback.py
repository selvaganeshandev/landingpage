"""Paid-model policy for the engine's OpenRouter calls.

Mirrors ``backend/core/model_fallback.py``. The two projects are separate
Django installs with separate settings modules, so the policy cannot simply be
imported across — but both read the same ``ALLOW_FREE_MODEL_FALLBACK`` name, so
one line in each ``.env`` turns free models off everywhere.

Why this exists: on 2026-09-21 the OpenRouter balance reached zero. Every paid
call 402'd and silently dropped to the shared `:free` pool, which is rate
limited and answers 429 ``overloaded`` under load. The user saw the free
model's 429 — the last failure in a chain of five — and nothing anywhere said
the balance was empty. Prompt generation ran on free models for an unknown
stretch with no indication in the UI that quality had changed.

This module returns MESSAGES rather than raising. The engine surfaces failures
as ``GenerationError`` (caught in two places in ``prompt_generation``), and
introducing a second exception type would slip straight past those handlers.
Callers wrap the message themselves.
"""

from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

OPENROUTER_CREDITS_URL = "https://openrouter.ai/settings/credits"

# Shown verbatim to whoever clicked "Generate with AI".
RECHARGE_MESSAGE = (
    "The OpenRouter credit is over. Please recharge the OpenRouter API key at "
    f"{OPENROUTER_CREDITS_URL} and try again."
)

UNAVAILABLE_MESSAGE = (
    "The AI provider is temporarily unavailable. Please try again in a moment."
)


def free_fallback_enabled() -> bool:
    """Whether `:free` models may be tried after the paid model fails.

    ``False`` in production (the default). Never raises — a missing or
    malformed setting means paid-only, which is the safe reading.
    """
    try:
        return bool(getattr(settings, "ALLOW_FREE_MODEL_FALLBACK", False))
    except Exception:  # noqa: BLE001 - settings access must never break a run
        return False


# Substrings that mark an exhausted balance rather than a transient fault.
# Matched case-insensitively against ``str(exc)``, which for the OpenAI client
# carries the full JSON error body OpenRouter returned.
_CREDIT_SIGNALS = (
    "402",
    "payment required",
    "insufficient",
    "insufficient_quota",
    "requires more credits",
    "out of credits",
    "negative balance",
    "billing",
    "quota exceeded",
    "exceeded your current quota",
)


def looks_like_credit_exhaustion(exc: BaseException | None) -> bool:
    """True when ``exc`` reads like an empty balance rather than a blip.

    Deliberately string-based: the client raises several exception types across
    providers and their structured fields are not consistent, but the
    402/credits wording is. A false negative only costs a less specific
    message, never a wrong action.
    """
    if exc is None:
        return False
    try:
        blob = str(exc).lower()
    except Exception:  # noqa: BLE001 - a weird __str__ must not break the handler
        return False
    if getattr(exc, "status_code", None) == 402:
        return True
    return any(signal in blob for signal in _CREDIT_SIGNALS)


def is_free_slug(model: str | None) -> bool:
    """True for an OpenRouter slug served from the free pool (``…:free``)."""
    return bool(model) and str(model).strip().lower().endswith(":free")


def paid_only_message(exc: BaseException | None, model: str = "") -> str:
    """The message to show when the paid model failed in paid-only mode.

    Recharge wording for a billing failure, retry wording for anything else,
    with the provider's own error appended so the log keeps the detail.
    """
    is_credits = looks_like_credit_exhaustion(exc)
    headline = RECHARGE_MESSAGE if is_credits else UNAVAILABLE_MESSAGE
    logger.error(
        "[PAID_MODEL_FAILED] model=%s credits_exhausted=%s error=%s",
        model, is_credits, exc,
    )
    return f"{headline} (model: {model}; {exc})"


def free_primary_message(model: str, setting_name: str) -> str | None:
    """Message when the PRIMARY model is itself a `:free` slug, else ``None``.

    Turning off the fallback achieves nothing if the configured primary is
    already free — which is how this deployment was set up
    (``OPENROUTER_INTERNAL_MODEL=nex-agi/nex-n2.5-mini:free``). Naming the
    setting is the only way that gets spotted.

    Returns ``None`` when free fallback is allowed, so a local box is
    unaffected.
    """
    if not is_free_slug(model) or free_fallback_enabled():
        return None
    logger.error(
        "[PAID_MODEL_MISCONFIGURED] %s=%s is a free slug while "
        "ALLOW_FREE_MODEL_FALLBACK=False", setting_name, model,
    )
    return (
        f"{setting_name} is set to the free model '{model}', but free models "
        f"are disabled. Point {setting_name} at a paid model (for example "
        f"openai/gpt-5-mini), or set ALLOW_FREE_MODEL_FALLBACK=True to allow "
        f"free models again."
    )
