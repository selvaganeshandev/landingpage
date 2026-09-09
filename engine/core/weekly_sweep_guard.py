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

  3. The cooldown lived in a JSON file under BASE_DIR, which made the guard
     PER-MACHINE. A sweep launched from a laptop pointed at the production
     database read that laptop's empty state file, allowed itself, and stamped
     the cooldown where the server could never see it — so the server's guard
     still believed no sweep had ever run. On 2026-07-23 a full sweep started
     that way at 03:44 with no trace in beat.log or worker.log. The state now
     lives in the shared database (``sweep_guard_state``), the one place every
     caller must reach, so a sweep started anywhere is visible everywhere.

This module holds three guards:

  * ``killswitch_block`` — refuse a sweep whose DB row has ``enabled=False``.
  * ``cooldown_block``   — refuse a sweep that starts too soon after the last one.
  * ``preflight_block``  — refuse a sweep when no enabled platform has a usable key.

The cooldown and preflight guards are advisory-by-design: they return a reason
dict instead of raising, and an operator can override with ``force=True``.
The KILL SWITCH is deliberately NOT overridable — ``force=True`` does not
bypass it. Turning a sweep back on is an explicit database edit
(``enable_sweep()``), so no ad-hoc invocation from any host can restart the
spend.

Config (engine/.env, read via settings):
    WEEKLY_SWEEP_COOLDOWN_DAYS=6        # 0 disables the cooldown guard
    WEEKLY_SWEEP_PREFLIGHT_ENABLED=True

Model imports are lazy (inside functions) so the module still imports without a
configured database, and so the guards can be unit-tested by stubbing
``_load_state``/``_save_state``.
"""
import logging
import os
import socket
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Sweep identifiers (also the keys used in the state file).
PROMPTS = "prompts"
COMPETITORS = "competitors"
# Second prompt tier: the domains that are swept monthly rather than weekly.
# It is a separate identifier ONLY so it gets its own cooldown stamp — see
# _KILLSWITCH_ALIAS for why it deliberately does not get its own kill switch.
PROMPTS_MONTHLY = "prompts_monthly"

# Which row's `enabled` flag governs each sweep.
#
# _load_state() falls back to enabled=True when a row is MISSING, which is the
# right default for a DB outage but the wrong one for a brand-new identifier: a
# fresh 'prompts_monthly' row would not exist, so the tier would start life
# switched ON and quietly re-open the spend that the 'prompts' kill switch was
# set to stop on 2026-07-23. Aliasing the monthly tier onto the 'prompts' row
# means one deliberate switch still governs every prompt sweep, whatever its
# cadence. Cooldowns stay per-identifier so the two tiers never block each other.
_KILLSWITCH_ALIAS = {
    PROMPTS_MONTHLY: PROMPTS,
}

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
# State (shared DB row per sweep type)
# ---------------------------------------------------------------------------
# Shape returned by _load_state(), used when the row is missing or the database
# is unreachable. Defaults are permissive for the cooldown (never run) but the
# kill switch defaults to enabled so a DB outage cannot silently stop all data
# collection — a wasted sweep costs money, a permanently skipped one costs the
# product.
_DEFAULT_ENTRY = {
    "enabled": True,
    "disabled_reason": "",
    "last_started_at": None,
    "runs": 0,
}


def _caller_id():
    """Best-effort 'who started this', stored for attribution.

    The 2026-07-23 incident took an hour of forensics to attribute because
    nothing recorded the origin of a sweep. Recording it costs one column.
    """
    try:
        return f"{socket.gethostname()}:{os.getpid()}"[:255]
    except Exception:
        return ""


def _model():
    """Lazy import so this module loads without Django apps being ready."""
    from shared_models.models import SweepGuardState

    return SweepGuardState


def _load_state(sweep):
    """Current guard row for `sweep` as a plain dict.

    Falls back to permissive defaults if the row is missing or the DB is
    unreachable — see _DEFAULT_ENTRY for why that direction.
    """
    try:
        row = _model().objects.filter(sweep=sweep).first()
    except Exception as e:
        logger.warning(f"[WeeklySweep] could not read guard state for {sweep}, allowing: {e}")
        return dict(_DEFAULT_ENTRY)
    if row is None:
        return dict(_DEFAULT_ENTRY)
    return {
        "enabled": bool(row.enabled),
        "disabled_reason": row.disabled_reason or "",
        "last_started_at": row.last_started_at,
        "runs": int(row.runs or 0),
    }


def last_started_at(sweep):
    """When the given sweep last began, or None if never / unreadable."""
    return _load_state(sweep).get("last_started_at")


def record_sweep_start(sweep, now=None):
    """Stamp a sweep as started.

    Called at the moment the sweep is admitted, BEFORE any work is enqueued, so
    that a crash midway still consumes the cooldown. Re-running a half-finished
    sweep is a deliberate act that should use force=True.

    Writes to the shared DB row, so a sweep started on ANY host consumes the
    cooldown for every other host.
    """
    now = now or timezone.now()
    try:
        row, _ = _model().objects.get_or_create(sweep=sweep)
        row.last_started_at = now
        # Plain increment rather than F(): concurrent sweeps are the very thing
        # this module prevents, and `runs` is only for observability.
        row.runs = int(row.runs or 0) + 1
        row.last_started_by = _caller_id()
        row.save(update_fields=["last_started_at", "runs", "last_started_by", "modified_at"])
    except Exception as e:
        # Never let a bookkeeping failure crash an admitted sweep, but say so
        # loudly: an unrecorded start means the next sweep is not cooldown-blocked.
        logger.error(f"[WeeklySweep] could not record sweep start for {sweep}: {e}")


def disable_sweep(sweep, reason=""):
    """Flip the kill switch OFF for `sweep`. Refuses every run, force included."""
    row, _ = _model().objects.get_or_create(sweep=sweep)
    row.enabled = False
    row.disabled_reason = str(reason or "")[:2000]
    row.save(update_fields=["enabled", "disabled_reason", "modified_at"])
    logger.warning("[WeeklySweep] %s sweep DISABLED: %s", sweep, reason)


def enable_sweep(sweep):
    """Flip the kill switch back ON for `sweep`. Deliberate operator action."""
    row, _ = _model().objects.get_or_create(sweep=sweep)
    row.enabled = True
    row.disabled_reason = ""
    row.save(update_fields=["enabled", "disabled_reason", "modified_at"])
    logger.warning("[WeeklySweep] %s sweep re-enabled", sweep)


# ---------------------------------------------------------------------------
# Guard 0 — kill switch (NOT bypassable with force)
# ---------------------------------------------------------------------------
def killswitch_block(sweep):
    """Reason dict if this sweep is switched off in the database, else None.

    Checked before `force`, so an ad-hoc `force=True` call from any host cannot
    restart a sweep an operator has deliberately turned off.

    Resolved through _KILLSWITCH_ALIAS, so every prompt tier consults the one
    'prompts' switch rather than each cadence owning a switch of its own.
    """
    governing = _KILLSWITCH_ALIAS.get(sweep, sweep)
    state = _load_state(governing)
    if state.get("enabled", True):
        return None
    return {
        "skipped": True,
        "reason": "disabled",
        "sweep": sweep,
        "governed_by": governing,
        "disabled_reason": state.get("disabled_reason") or "",
        "hint": "re-enable with weekly_sweep_guard.enable_sweep(<sweep>)",
    }


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

    Order matters: the kill switch is evaluated BEFORE `force`, so a deliberate
    shutdown cannot be undone by passing force=True from a shell on any host.
    Only the cooldown and preflight guards are force-overridable.
    """
    disabled = killswitch_block(sweep)
    if disabled:
        logger.warning(
            "[WeeklySweep] %s sweep refused — kill switch is off%s",
            sweep,
            " (force ignored)" if force else "",
        )
        return disabled

    if force:
        logger.warning("[WeeklySweep] %s sweep forced — cooldown/preflight bypassed", sweep)
        return None
    return cooldown_block(sweep, now=now) or preflight_block()
