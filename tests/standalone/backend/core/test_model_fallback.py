"""
Tests for the paid-model policy.

These exist because of a real failure on 2026-09-21. "Generate Content" died
with a red toast quoting a 429 from `z-ai/glm-5.2:free` — "Provider returned
error / overloaded / upstream_provider_shared_pool". That model is LAST in the
free fallback chain, so the message was the fourth failure, not the first:
the paid model had already failed (almost certainly an empty balance), then two
other free models, and only the final one's complaint reached the user. Anyone
reading that toast goes looking at a free model they never chose to use.

Two separate defects were found, and both are covered here:

  - the fallback itself ......... a $0 balance degraded silently onto the shared
                                  free pool, which is rate limited and answers
                                  429 under load
  - the PRIMARY model ........... backend/.env had
                                  OPENROUTER_INTERNAL_MODEL=nex-agi/nex-n2.5-mini:free,
                                  so chat and domain analysis were on the free
                                  pool by CONFIGURATION. Removing the fallback
                                  alone would have changed nothing there.

The module under test imports Django settings but touches no database, network
or SDK, so this runs with a minimal settings stub.

Run:  python tests/standalone/backend/core/test_model_fallback.py
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_ROOT / 'backend'))

import django
from django.conf import settings as dj_settings

if not dj_settings.configured:
    dj_settings.configure(DEBUG=True, ALLOW_FREE_MODEL_FALLBACK=False)
    django.setup()

from core.model_fallback import (  # noqa: E402
    PaidModelUnavailable,
    RECHARGE_MESSAGE,
    UNAVAILABLE_MESSAGE,
    assert_paid_model,
    free_fallback_enabled,
    is_free_slug,
    looks_like_credit_exhaustion,
    paid_only_error,
)

_PASS, _FAIL = [], []


def check(name, condition, detail=''):
    (_PASS if condition else _FAIL).append(name)
    print(f"  {'PASS' if condition else 'FAIL'}  {name}"
          f"{('  -> ' + str(detail)) if detail and not condition else ''}")


def set_flag(value):
    """Flip ALLOW_FREE_MODEL_FALLBACK on the configured settings object."""
    dj_settings.ALLOW_FREE_MODEL_FALLBACK = value


# --------------------------------------------------------------------------- #
print("\nthe default is paid-only")
# --------------------------------------------------------------------------- #
set_flag(False)
check("free fallback is OFF by default", free_fallback_enabled() is False)
set_flag(True)
check("the flag turns it back on", free_fallback_enabled() is True)
set_flag(False)

# --------------------------------------------------------------------------- #
print("\nan exhausted balance is told apart from a busy provider")
# --------------------------------------------------------------------------- #
# The real 402 bodies OpenRouter returns, and the real 429 from the incident.
credit_errors = [
    "Error code: 402 - Payment Required",
    "Error code: 402 - {'error': {'message': 'Insufficient credits'}}",
    "This request requires more credits, or fewer max_tokens",
    "You have exceeded your current quota",
    "negative balance on this account",
]
for msg in credit_errors:
    check(f"credits: {msg[:44]}", looks_like_credit_exhaustion(Exception(msg)) is True)

transient_errors = [
    # The exact shape from the incident toast.
    "Error code: 429 - {'error': {'message': 'Provider returned error', 'code': 429, "
    "'metadata': {'raw': 'z-ai/glm-5.2:free is temporarily rate-limited upstream'}}}",
    "Connection timed out after 30s",
    "Error code: 503 - upstream unavailable",
]
for msg in transient_errors:
    check(f"transient: {msg[:44]}", looks_like_credit_exhaustion(Exception(msg)) is False)

check("None is not a credit error", looks_like_credit_exhaustion(None) is False)


class _Hostile:
    """__str__ raises — the detector must not take a request down with it."""
    def __str__(self):
        raise RuntimeError("boom")


check("a broken __str__ is survived", looks_like_credit_exhaustion(_Hostile()) is False)


class _WithStatus(Exception):
    status_code = 402


check("a 402 status_code is honoured even with bland text",
      looks_like_credit_exhaustion(_WithStatus("something went wrong")) is True)

# --------------------------------------------------------------------------- #
print("\nthe user is told which of the two happened")
# --------------------------------------------------------------------------- #
credit_exc = paid_only_error(Exception("Error code: 402 - insufficient credits"),
                             "anthropic/claude-sonnet-4.5")
check("an empty balance says to recharge", RECHARGE_MESSAGE in str(credit_exc))
check("the recharge message links the credits page",
      "openrouter.ai/settings/credits" in str(credit_exc))

busy_exc = paid_only_error(Exception("Error code: 429 - overloaded"), "anthropic/claude-sonnet-4.5")
check("a busy provider says to retry", UNAVAILABLE_MESSAGE in str(busy_exc))
check("a busy provider does NOT say to recharge", RECHARGE_MESSAGE not in str(busy_exc))

# The provider's own error must NOT reach the user. A real 402/429 body carries
# 'metadata', 'remedy_hint', 'headers' and a user_id, and appending it put that
# whole wall of JSON in a red box on screen — the exact thing these messages
# exist to replace.
check("no raw provider error in the user's message", "429" not in str(busy_exc))
check("no JSON blob in the user's message", "{" not in str(busy_exc))
check("the message stays short", len(str(busy_exc)) < 160, len(str(busy_exc)))
check("the cause is retrievable for code", busy_exc.cause is not None)
check("the provider detail survives on the cause", "429" in str(busy_exc.cause))
check("the model is retrievable", busy_exc.model == "anthropic/claude-sonnet-4.5")

# Every existing caller wraps these paths in `except Exception`. If this stops
# being an Exception subclass, a failure escapes the handler and 500s raw.
check("PaidModelUnavailable is an Exception", isinstance(credit_exc, Exception))

# --------------------------------------------------------------------------- #
print("\na free slug is recognised")
# --------------------------------------------------------------------------- #
check("z-ai/glm-5.2:free is free", is_free_slug("z-ai/glm-5.2:free") is True)
check("the .env value is free", is_free_slug("nex-agi/nex-n2.5-mini:free") is True)
check("trailing whitespace still matches", is_free_slug("  z-ai/glm-5.2:FREE  ") is True)
check("openai/gpt-5-mini is not free", is_free_slug("openai/gpt-5-mini") is False)
check("a slug merely containing 'free' is not free",
      is_free_slug("vendor/freeform-7b") is False)
check("None is not free", is_free_slug(None) is False)
check("empty is not free", is_free_slug("") is False)

# --------------------------------------------------------------------------- #
print("\na free PRIMARY model is refused in paid-only mode")
# --------------------------------------------------------------------------- #
# This is the defect the fallback change alone would have missed.
set_flag(False)
try:
    assert_paid_model("nex-agi/nex-n2.5-mini:free", "OPENROUTER_INTERNAL_MODEL")
    check("a free primary is rejected", False, "accepted, should have raised")
except PaidModelUnavailable as exc:
    check("a free primary is rejected", True)
    check("the error names the setting to fix", "OPENROUTER_INTERNAL_MODEL" in str(exc))
    check("the error names the offending slug", "nex-agi/nex-n2.5-mini:free" in str(exc))
    check("the error suggests a paid model", "openai/gpt-5-mini" in str(exc))
    check("the error names the escape hatch", "ALLOW_FREE_MODEL_FALLBACK" in str(exc))


def accepts_model(name, model):
    try:
        assert_paid_model(model, "OPENROUTER_INTERNAL_MODEL")
        check(name, True)
    except Exception as exc:  # noqa: BLE001
        check(name, False, f"raised: {exc}")


accepts_model("a paid primary passes", "openai/gpt-5-mini")
accepts_model("a paid Claude primary passes", "anthropic/claude-sonnet-4.5")

# With the flag on, a free primary is a deliberate local choice, not a fault.
set_flag(True)
accepts_model("a free primary is allowed when the flag is on", "nex-agi/nex-n2.5-mini:free")
set_flag(False)

print(f"\n{len(_PASS)} passed, {len(_FAIL)} failed")
if _FAIL:
    for name in _FAIL:
        print(f"  FAILED: {name}")
sys.exit(1 if _FAIL else 0)
