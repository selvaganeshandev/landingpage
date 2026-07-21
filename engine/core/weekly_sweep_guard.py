"""
Cost guards for the weekly full-corpus reprocess sweeps.

A weekly sweep resets EVERY prompt (or competitor) to INIT and re-queries every
enabled platform. At ~2,700 prompts x 4 platforms that is ~10,800 LLM API calls
per run, so a sweep is by far the most expensive thing the engine does. Two
things made it cost more than intended:

  1. Nothing stopped a *second* sweep being launched by hand days after the
     Sunday cron had already run. Four full sweeps ran in the nine days to
     2026-07-21 — roughly 43,000 calls instead of ~11,000 — and the last one
     drained a fresh credit top-up within five hours.
  2. A sweep would start happily with every provider key already out of
     credits, churning the whole queue for nothing and leaving thousands of
     prompts stranded in INIT.

This module holds both guards:

  * ``cooldown_block``  — refuse a sweep that starts too soon after the last one.
  * ``preflight_block`` — refuse a sweep when no enabled platform has a usable key.

Both are advisory-by-design: they return a reason dict instead of raising, and
an operator can always override with ``force=True``.

Config (engine/.env, read via settings):
    WEEKLY_SWEEP_COOLDOWN_DAYS=6        # 0 disables the cooldown guard
    WEEKLY_SWEEP_PREFLIGHT_ENABLED=True
    WEEKLY_SWEEP_STATE_FILE=<BASE_DIR>/weekly_sweep_state.json

Imports no models, so it stays unit-testable without a database.
"""
import json
import logging
import os
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Sweep identifiers (also the keys used in the state file).
PROMPTS = "prompts"
COMPETITORS = "competitors"

# ENABLED_PLATFORMS uses pipeline platform names; quota_monitor probes are keyed
# by provider. Mirrors the dispatch in PromptAnalyticsProcessor._process_prompt.
PLATFORM_PROVIDERS = {
    "chatgpt": "openai",
    "gemini": "gemini",
    "perplexity": "perplexity",
    "claude": "anthropic",
    "grok": "xai",
    "deepseek": "deepseek",
}

# States that prove a key cannot serve traffic right now. Deliberately narrower
# than quota_monitor.BAD_STATES: ERROR is usually a transient probe/network
# blip, and MODEL_UNAVAILABLE only tells us about the cheap *probe* model, which
# is not the model the pipeline uses. Blocking a sweep on either of those would
# silently stop all data collection over a false signal, which is worse than a
# wasted sweep — so anything uncertain counts as usable.
UNUSABLE_STATES = {"OUT_OF_CREDITS", "INVALID_KEY", "NOT_CONFIGURED"}


def _cfg(name, default):
    return getattr(settings, name, default)


# ---------------------------------------------------------------------------
# State file (last sweep start per sweep type)
# ---------------------------------------------------------------------------
def _state_path():
    base = str(_cfg("BASE_DIR", os.getcwd()))
    return _cfg("WEEKLY_SWEEP_STATE_FILE", os.path.join(base, "weekly_sweep_state.json"))


def _load_state():
    try:
        with open(_state_path(), "r") as fh:
            state = json.load(fh)
        return state if isinstance(state, dict) else {}
    except Exception:
        return {}


def _save_state(state):
    """Write the sweep state atomically.

    A half-written file would be unreadable next run, which would silently
    forget the last sweep and re-open the door to the double-spend this module
    exists to prevent — so write to a temp file and swap it in.
    """
    path = _state_path()
    tmp = f"{path}.tmp"
    try:
        with open(tmp, "w") as fh:
            json.dump(state, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception as e:
        logger.warning(f"[WeeklySweep] could not save state: {e}")


def _parse_ts(value):
    """Parse an ISO timestamp from the state file; None if missing/corrupt."""
    if not value:
        return None
    try:
        return timezone.datetime.fromisoformat(value)
    except Exception:
        return None


def last_started_at(sweep):
    """When the given sweep last began, or None if never / unreadable."""
    entry = _load_state().get(sweep) or {}
    return _parse_ts(entry.get("last_started_at"))


def record_sweep_start(sweep, now=None):
    """Stamp a sweep as started.

    Called at the moment the sweep is admitted, BEFORE any work is enqueued, so
    that a crash midway still consumes the cooldown. Re-running a half-finished
    sweep is a deliberate act that should use force=True.
    """
    now = now or timezone.now()
    state = _load_state()
    entry = dict(state.get(sweep) or {})
    entry["last_started_at"] = now.isoformat()
    entry["runs"] = int(entry.get("runs") or 0) + 1
    _save_state({**state, sweep: entry})


# ---------------------------------------------------------------------------
# Guard 1 — cooldown
# ---------------------------------------------------------------------------
def cooldown_block(sweep, now=None):
    """Reason dict if this sweep is still inside its cooldown window, else None."""
    days = float(_cfg("WEEKLY_SWEEP_COOLDOWN_DAYS", 6))
    if days <= 0:
        return None

    last = last_started_at(sweep)
    if last is None:
        return None

    now = now or timezone.now()
    try:
        elapsed = now - last
    except TypeError as e:
        # Naive/aware mismatch (USE_TZ flipped between runs). Fail open: a
        # skipped sweep costs a week of data, a wasted sweep only costs money.
        logger.warning(f"[WeeklySweep] could not compare sweep timestamps, allowing: {e}")
        return None
    window = timedelta(days=days)
    if elapsed >= window:
        return None

    remaining = window - elapsed
    return {
        "skipped": True,
        "reason": "cooldown",
        "sweep": sweep,
        "last_started_at": last.isoformat(),
        "cooldown_days": days,
        "hours_remaining": round(remaining.total_seconds() / 3600, 1),
    }


# ---------------------------------------------------------------------------
# Guard 2 — provider preflight
# ---------------------------------------------------------------------------
def _provider_states():
    """Map provider -> set of observed key states, across system and BYOK keys.

    quota_monitor keys results as "openai" (system/.env) and "openai@org1"
    (that org's BYOK key), so both collapse onto the same provider here.
    """
    from .quota_monitor import check_all_quotas

    states = {}
    for result in check_all_quotas() or []:
        key = str(result.get("key") or "")
        provider = key.split("@", 1)[0]
        if not provider:
            continue
        states.setdefault(provider, set()).add(result.get("state") or "ERROR")
    return states


def preflight_block():
    """Reason dict if NO enabled platform has a usable key, else None.

    Blocks only when every enabled platform is definitively unusable. If even
    one platform can still answer, the sweep proceeds — partial data beats no
    data — and the dead platforms are logged.
    """
    if not _cfg("WEEKLY_SWEEP_PREFLIGHT_ENABLED", True):
        return None

    platforms = list(_cfg("ENABLED_PLATFORMS", ["chatgpt"]) or [])
    if not platforms:
        return None

    try:
        states = _provider_states()
    except Exception as e:
        # Never let a probe failure block data collection.
        logger.warning(f"[WeeklySweep] preflight probe failed, allowing sweep: {e}")
        return None

    usable, unusable = [], {}
    for platform in platforms:
        provider = PLATFORM_PROVIDERS.get(platform, platform)
        observed = states.get(provider)
        if not observed or observed - UNUSABLE_STATES:
            # Unprobed or at least one key in a non-fatal state → usable.
            usable.append(platform)
        else:
            unusable[platform] = sorted(observed)

    if usable:
        if unusable:
            logger.warning(
                "[WeeklySweep] proceeding with %s; no usable key for %s",
                ", ".join(usable), ", ".join(sorted(unusable)),
            )
        return None

    return {
        "skipped": True,
        "reason": "no_usable_provider",
        "unusable": unusable,
    }


# ---------------------------------------------------------------------------
# Combined entry check
# ---------------------------------------------------------------------------
def sweep_blocked(sweep, force=False, now=None):
    """Reason dict if this sweep must not start, else None.

    Call once when a sweep is *entered* (not for chained continuation batches),
    and call record_sweep_start() when it returns None.
    """
    if force:
        logger.warning("[WeeklySweep] %s sweep forced — guards bypassed", sweep)
        return None
    return cooldown_block(sweep, now=now) or preflight_block()
