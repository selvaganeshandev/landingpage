"""Paid-model policy for every OpenRouter call the backend makes.

Production runs **paid models only**. Four call paths used to fall back to
`:free` OpenRouter models when the paid model failed — content generation and
humanisation, keyword suggestions, the chatbot, and domain analysis. That kept
the product alive on a $0 balance, but it did so silently and at a cost:

  * the free pool is shared across all of OpenRouter, so it answers 429
    ``overloaded`` under load and the job dies anyway,
  * output quality drops without anyone being told,
  * and the error the user finally sees names a *free* model, which sends
    whoever debugs it looking in the wrong place. The real cause — an empty
    paid balance — is three failures further up the chain and never surfaces.

So the fallback is off by default and an exhausted key now says so in plain
words. ``ALLOW_FREE_MODEL_FALLBACK=True`` restores the old behaviour without a
deploy, for a local box or a deliberate degraded mode.

Everything here is defensive: ``free_fallback_enabled`` never raises, and
``PaidModelUnavailable`` subclasses ``Exception`` so every existing
``except Exception`` handler (the humanisation ``_pass_or_keep`` guard, the DRF
view wrappers) keeps catching it exactly as before.
"""

from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# Where an admin actually goes to fix an empty balance.
OPENROUTER_CREDITS_URL = "https://openrouter.ai/settings/credits"

# Shown to the user verbatim when the paid model is out of credits. Written for
# whoever is staring at the red toast, not for a log reader.
RECHARGE_MESSAGE = (
    "The OpenRouter API key has run out of credits. "
    f"Please recharge it at {OPENROUTER_CREDITS_URL} and try again."
)

# Shown when the paid model failed for some reason that is NOT billing —
# an overloaded provider, a timeout, a bad slug. Retrying is the right advice.
UNAVAILABLE_MESSAGE = (
    "The AI provider is temporarily unavailable. Please try again in a moment."
)


class PaidModelUnavailable(Exception):
    """The paid model failed and free-model fallback is disabled.

    Subclasses ``Exception`` on purpose: callers already wrap these paths in
    ``except Exception``, and this must not slip past a handler that used to
    catch the raw provider error.
    """

    def __init__(self, message: str, *, model: str = "", cause: BaseException | None = None):
        super().__init__(message)
        self.model = model
        self.cause = cause


def free_fallback_enabled() -> bool:
    """Whether `:free` models may be tried after the paid model fails.

    ``False`` in production (the default). Never raises — a missing or
    malformed setting means paid-only, which is the safe reading.
    """
    try:
        return bool(getattr(settings, "ALLOW_FREE_MODEL_FALLBACK", False))
    except Exception:  # noqa: BLE001 - settings access must never break a request
        return False


# Substrings that mark an exhausted balance rather than a transient fault.
# Matched case-insensitively against ``str(exc)``, which for the OpenRouter
# client carries the full JSON error body.
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

    Deliberately string-based. The OpenRouter client raises several exception
    types across providers and the structured fields are not consistent between
    them, but the 402/credits wording is. A false negative only costs a slightly
    less specific message, never a wrong action.
    """
    if exc is None:
        return False
    try:
        blob = str(exc).lower()
    except Exception:  # noqa: BLE001 - a weird __str__ must not break the handler
        return False
    status = getattr(exc, "status_code", None)
    if status == 402:
        return True
    return any(signal in blob for signal in _CREDIT_SIGNALS)


def is_free_slug(model: str | None) -> bool:
    """True for an OpenRouter slug served from the free pool (``…:free``)."""
    return bool(model) and str(model).strip().lower().endswith(":free")


def assert_paid_model(model: str, setting_name: str) -> None:
    """Refuse to run a `:free` slug as the PRIMARY model in paid-only mode.

    Turning off the fallback is pointless if the configured primary is itself
    free — which is exactly how this environment was set up
    (``OPENROUTER_INTERNAL_MODEL=nex-agi/nex-n2.5-mini:free``), so chat and
    domain analysis were on the shared pool by configuration, not by fallback.
    Failing loudly with the setting name is the only way that gets noticed.

    No-op when free fallback is allowed, so a local box is unaffected.
    """
    if not is_free_slug(model) or free_fallback_enabled():
        return
    logger.error(
        "[PAID_MODEL_MISCONFIGURED] %s=%s is a free slug while "
        "ALLOW_FREE_MODEL_FALLBACK=False", setting_name, model,
    )
    raise PaidModelUnavailable(
        f"{setting_name} is set to the free model '{model}', but free models "
        f"are disabled. Point {setting_name} at a paid model "
        f"(for example openai/gpt-5-mini), or set "
        f"ALLOW_FREE_MODEL_FALLBACK=True to allow free models again.",
        model=model,
    )


def paid_only_error(exc: BaseException | None, model: str = "") -> PaidModelUnavailable:
    """Build the exception to raise when the paid model failed, paid-only mode.

    Picks the recharge wording for a billing failure and the try-again wording
    for anything else, then appends the underlying provider error so the log
    still carries what actually happened.
    """
    is_credits = looks_like_credit_exhaustion(exc)
    headline = RECHARGE_MESSAGE if is_credits else UNAVAILABLE_MESSAGE
    detail = f" (model: {model}; {exc})" if exc is not None else f" (model: {model})"
    logger.error(
        "[PAID_MODEL_FAILED] model=%s credits_exhausted=%s error=%s",
        model, is_credits, exc,
    )
    return PaidModelUnavailable(headline + detail, model=model, cause=exc)
