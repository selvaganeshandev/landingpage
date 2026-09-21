"""
Tests for the engine's paid-model policy.

Companion to ``tests/standalone/backend/core/test_model_fallback.py``. The
engine is a separate Django install with its own settings module, so the policy
is mirrored rather than imported — these tests exist to keep the two copies
honest about the behaviour that matters.

One deliberate difference from the backend copy, and it is the whole reason
this module returns strings instead of raising: the engine surfaces failures as
``GenerationError``, and ``prompt_generation`` catches that type in two places.
A new exception class would slip straight past both handlers, turning a handled
failure into an unhandled one. So the policy hands back a message and the
caller wraps it.

Background — 2026-09-21: the OpenRouter balance hit zero, every paid call
402'd, and "Generate with AI" quietly finished on the shared `:free` pool. The
only visible symptom was a 429 from the LAST free model in the chain, which
named a model nobody had chosen and said nothing about the balance.

Run:  python tests/standalone/engine/core/test_model_fallback.py
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_ROOT / 'engine'))

import django
from django.conf import settings as dj_settings

if not dj_settings.configured:
    dj_settings.configure(DEBUG=True, ALLOW_FREE_MODEL_FALLBACK=False)
    django.setup()

from core.model_fallback import (  # noqa: E402
    RECHARGE_MESSAGE,
    UNAVAILABLE_MESSAGE,
    free_fallback_enabled,
    free_primary_message,
    is_free_slug,
    looks_like_credit_exhaustion,
    paid_only_message,
)

_PASS, _FAIL = [], []


def check(name, condition, detail=''):
    (_PASS if condition else _FAIL).append(name)
    print(f"  {'PASS' if condition else 'FAIL'}  {name}"
          f"{('  -> ' + str(detail)) if detail and not condition else ''}")


def set_flag(value):
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
for msg in [
    "Error code: 402 - Payment Required",
    "Error code: 402 - {'error': {'message': 'Insufficient credits'}}",
    "This request requires more credits, or fewer max_tokens",
    "You have exceeded your current quota",
]:
    check(f"credits: {msg[:42]}", looks_like_credit_exhaustion(Exception(msg)) is True)

for msg in [
    # The 429 from the incident, verbatim in shape.
    "Error code: 429 - {'error': {'message': 'Provider returned error', 'code': 429, "
    "'metadata': {'raw': 'z-ai/glm-5.2:free is temporarily rate-limited upstream'}}}",
    "Connection timed out after 90s",
]:
    check(f"transient: {msg[:42]}", looks_like_credit_exhaustion(Exception(msg)) is False)

check("None is not a credit error", looks_like_credit_exhaustion(None) is False)


class _Hostile:
    def __str__(self):
        raise RuntimeError("boom")


check("a broken __str__ is survived", looks_like_credit_exhaustion(_Hostile()) is False)

# --------------------------------------------------------------------------- #
print("\nthe user is told the credit is over")
# --------------------------------------------------------------------------- #
credits_msg = paid_only_message(Exception("Error code: 402 - insufficient credits"),
                                "openai/gpt-5-mini")
check("says the credit is over", "credit is over" in credits_msg.lower())
check("says to recharge", "recharge" in credits_msg.lower())
check("links the credits page", "openrouter.ai/settings/credits" in credits_msg)
check("matches the shared constant", RECHARGE_MESSAGE in credits_msg)

busy_msg = paid_only_message(Exception("Error code: 429 - overloaded"), "openai/gpt-5-mini")
check("a busy provider says to retry", UNAVAILABLE_MESSAGE in busy_msg)
check("a busy provider does NOT mention credits",
      "recharge" not in busy_msg.lower())
check("the provider error is kept for the log",
      "429" in busy_msg and "openai/gpt-5-mini" in busy_msg)

# --------------------------------------------------------------------------- #
print("\na free slug is recognised")
# --------------------------------------------------------------------------- #
for slug in ["z-ai/glm-5.2:free", "nex-agi/nex-n2.5-mini:free",
             "nvidia/nemotron-3-super-120b-a12b:free", "  google/gemma-4-31b-it:FREE  "]:
    check(f"free: {slug.strip()[:40]}", is_free_slug(slug) is True)

for slug in ["openai/gpt-5-mini", "anthropic/claude-sonnet-4.5",
             "vendor/freeform-7b", None, ""]:
    check(f"not free: {slug!r}", is_free_slug(slug) is False)

# --------------------------------------------------------------------------- #
print("\na free PRIMARY model is refused in paid-only mode")
# --------------------------------------------------------------------------- #
set_flag(False)
problem = free_primary_message("nex-agi/nex-n2.5-mini:free", "OPENROUTER_INTERNAL_MODEL")
check("a free primary is refused", problem is not None)
check("the message names the setting", "OPENROUTER_INTERNAL_MODEL" in (problem or ""))
check("the message names the slug", "nex-agi/nex-n2.5-mini:free" in (problem or ""))
check("the message suggests a paid model", "openai/gpt-5-mini" in (problem or ""))
check("the message names the escape hatch", "ALLOW_FREE_MODEL_FALLBACK" in (problem or ""))

check("a paid primary is fine",
      free_primary_message("openai/gpt-5-mini", "OPENROUTER_INTERNAL_MODEL") is None)

set_flag(True)
check("a free primary is allowed when the flag is on",
      free_primary_message("nex-agi/nex-n2.5-mini:free", "OPENROUTER_INTERNAL_MODEL") is None)
set_flag(False)

# --------------------------------------------------------------------------- #
print("\nthe two projects agree on the switch")
# --------------------------------------------------------------------------- #
# One .env line must turn free models off in both installs, so the setting name
# has to stay identical. A rename on one side only would silently re-enable
# free models there.
_backend_policy = (_ROOT / 'backend' / 'core' / 'model_fallback.py').read_text(encoding='utf-8')
check("the backend reads the same setting name",
      'ALLOW_FREE_MODEL_FALLBACK' in _backend_policy)
check("the backend also links the credits page",
      'openrouter.ai/settings/credits' in _backend_policy)

print(f"\n{len(_PASS)} passed, {len(_FAIL)} failed")
if _FAIL:
    for name in _FAIL:
        print(f"  FAILED: {name}")
sys.exit(1 if _FAIL else 0)
