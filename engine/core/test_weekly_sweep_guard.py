"""
Tests for the weekly full-corpus sweep cost guards.

A sweep is ~10,800 LLM calls, so the two things that must hold are: a second
sweep inside the cooldown window is refused, and a sweep with every provider
key dead is refused. Everything else must be allowed through — a guard that
wrongly blocks stops all data collection, which is worse than a wasted sweep.

weekly_sweep_guard touches Django only for `settings` and `timezone`, so this
stubs both and loads the module directly, matching test_quota_monitor.py. No
database, environment, or network access required.

Run:  python core/test_weekly_sweep_guard.py
"""
import importlib.util
import json
import os
import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone as _tz

_NOW = [datetime(2026, 7, 21, 6, 0, tzinfo=_tz.utc)]
_QUOTA_RESULTS = [[]]


class _Settings:
    """Minimal stand-in for django.conf.settings."""

    def _apply(self, values):
        for name in [n for n in vars(self)]:
            delattr(self, name)
        for name, value in values.items():
            setattr(self, name, value)


class _Clock:
    """Controllable stand-in for django.utils.timezone."""

    @staticmethod
    def now():
        return _NOW[0]

    datetime = datetime


def _load_guard():
    """Import weekly_sweep_guard with Django and quota_monitor stubbed out."""
    settings = _Settings()
    conf = types.ModuleType('django.conf')
    conf.settings = settings
    utils = types.ModuleType('django.utils')
    utils.timezone = _Clock
    sys.modules.update({
        'django': types.ModuleType('django'),
        'django.conf': conf,
        'django.utils': utils,
    })

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weekly_sweep_guard.py')
    spec = importlib.util.spec_from_file_location('weekly_sweep_guard_undertest', path)
    module = importlib.util.module_from_spec(spec)
    # The module does `from .quota_monitor import check_all_quotas` lazily inside
    # _provider_states, so give it a package-free stand-in.
    stub = types.ModuleType('quota_monitor_stub')
    stub.check_all_quotas = lambda: _QUOTA_RESULTS[0]
    sys.modules['weekly_sweep_guard_undertest.quota_monitor'] = stub
    module.__package__ = 'weekly_sweep_guard_undertest'
    sys.modules['weekly_sweep_guard_undertest'] = module
    spec.loader.exec_module(module)
    return module, settings


GUARD, SETTINGS = _load_guard()

_PASS, _FAIL = [], []


def check(name, condition, detail=''):
    (_PASS if condition else _FAIL).append(name)
    print(f"  {'PASS' if condition else 'FAIL'}  {name}{('  -> ' + str(detail)) if detail and not condition else ''}")


def reset(**overrides):
    """Fresh state file + default settings, with per-test overrides."""
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    os.unlink(path)
    values = {
        'WEEKLY_SWEEP_STATE_FILE': path,
        'WEEKLY_SWEEP_COOLDOWN_DAYS': 6,
        'WEEKLY_SWEEP_PREFLIGHT_ENABLED': True,
        'ENABLED_PLATFORMS': ['chatgpt', 'gemini', 'claude', 'perplexity'],
    }
    values.update(overrides)
    SETTINGS._apply(values)
    _NOW[0] = datetime(2026, 7, 21, 6, 0, tzinfo=_tz.utc)
    _QUOTA_RESULTS[0] = [{'key': p, 'state': 'OK'} for p in
                         ('openai', 'gemini', 'anthropic', 'perplexity')]
    return path


def advance(days=0, hours=0):
    _NOW[0] = _NOW[0] + timedelta(days=days, hours=hours)


# ---------------------------------------------------------------------------
print('\nCooldown guard')
# ---------------------------------------------------------------------------
reset()
check('first ever sweep is allowed', GUARD.sweep_blocked(GUARD.PROMPTS) is None)

reset()
GUARD.record_sweep_start(GUARD.PROMPTS)
blocked = GUARD.sweep_blocked(GUARD.PROMPTS)
check('immediate second sweep is blocked', blocked is not None and blocked['reason'] == 'cooldown', blocked)
check('block reports hours remaining', blocked and blocked['hours_remaining'] == 144.0, blocked)

# The real incident: cron ran Sunday, a manual sweep was fired two days later.
reset()
GUARD.record_sweep_start(GUARD.PROMPTS)
advance(days=2, hours=10)
blocked = GUARD.sweep_blocked(GUARD.PROMPTS)
check('manual sweep 2 days later is blocked', blocked is not None and blocked['reason'] == 'cooldown', blocked)

reset()
GUARD.record_sweep_start(GUARD.PROMPTS)
advance(days=6, hours=1)
check('next weekly sweep is allowed after cooldown', GUARD.sweep_blocked(GUARD.PROMPTS) is None)

# 7-day cron with a 6-day cooldown must never block itself, even with jitter.
reset()
GUARD.record_sweep_start(GUARD.PROMPTS)
advance(days=7)
check('sunday cron 7 days later is allowed', GUARD.sweep_blocked(GUARD.PROMPTS) is None)

reset()
GUARD.record_sweep_start(GUARD.PROMPTS)
check('force=True overrides the cooldown', GUARD.sweep_blocked(GUARD.PROMPTS, force=True) is None)

# Prompts and competitors are separate sweeps an hour apart; one must not
# consume the other's cooldown.
reset()
GUARD.record_sweep_start(GUARD.PROMPTS)
advance(hours=1)
check('competitor sweep unaffected by prompt sweep', GUARD.sweep_blocked(GUARD.COMPETITORS) is None)

reset(WEEKLY_SWEEP_COOLDOWN_DAYS=0)
GUARD.record_sweep_start(GUARD.PROMPTS)
check('cooldown_days=0 disables the guard', GUARD.sweep_blocked(GUARD.PROMPTS) is None)

# A corrupt or truncated state file must not wedge sweeps forever.
path = reset()
with open(path, 'w') as fh:
    fh.write('{not json')
check('corrupt state file does not block', GUARD.sweep_blocked(GUARD.PROMPTS) is None)

path = reset()
with open(path, 'w') as fh:
    json.dump({'prompts': {'last_started_at': 'not-a-timestamp'}}, fh)
check('unparseable timestamp does not block', GUARD.sweep_blocked(GUARD.PROMPTS) is None)

# USE_TZ flipped between runs: comparing naive to aware raises, and a raising
# guard would stop data collection entirely. Must fail open.
path = reset()
with open(path, 'w') as fh:
    json.dump({'prompts': {'last_started_at': datetime(2026, 7, 21, 5, 0).isoformat()}}, fh)
check('naive/aware timestamp mismatch does not block',
      GUARD.sweep_blocked(GUARD.PROMPTS) is None)

path = reset()
GUARD.record_sweep_start(GUARD.PROMPTS)
check('start is persisted to disk', os.path.exists(path))
check('start timestamp round-trips', GUARD.last_started_at(GUARD.PROMPTS) == _NOW[0],
      GUARD.last_started_at(GUARD.PROMPTS))
GUARD.record_sweep_start(GUARD.COMPETITORS)
advance(days=7)
GUARD.record_sweep_start(GUARD.PROMPTS)
with open(path) as fh:
    saved = json.load(fh)
check('run counter increments per sweep', saved['prompts']['runs'] == 2, saved)
check('recording one sweep preserves the other', saved['competitors']['runs'] == 1, saved)


# ---------------------------------------------------------------------------
print('\nPreflight guard')
# ---------------------------------------------------------------------------
reset()
check('all providers OK is allowed', GUARD.preflight_block() is None)

reset()
_QUOTA_RESULTS[0] = [{'key': p, 'state': 'OUT_OF_CREDITS'} for p in
                     ('openai', 'gemini', 'anthropic', 'perplexity')]
blocked = GUARD.preflight_block()
check('every provider out of credits is blocked',
      blocked is not None and blocked['reason'] == 'no_usable_provider', blocked)

# Partial outage: some data beats no data.
reset()
_QUOTA_RESULTS[0] = [
    {'key': 'openai', 'state': 'OK'},
    {'key': 'gemini', 'state': 'OUT_OF_CREDITS'},
    {'key': 'anthropic', 'state': 'OUT_OF_CREDITS'},
    {'key': 'perplexity', 'state': 'INVALID_KEY'},
]
check('one healthy provider still allows the sweep', GUARD.preflight_block() is None)

# BYOK: the org key is what actually runs the pipeline, so a dead .env key with
# a healthy org key must not block.
reset()
_QUOTA_RESULTS[0] = [
    {'key': 'openai', 'state': 'OUT_OF_CREDITS'},
    {'key': 'openai@org1', 'state': 'OK'},
    {'key': 'gemini', 'state': 'OUT_OF_CREDITS'},
    {'key': 'anthropic', 'state': 'OUT_OF_CREDITS'},
    {'key': 'perplexity', 'state': 'OUT_OF_CREDITS'},
]
check('healthy BYOK key rescues a dead system key', GUARD.preflight_block() is None)

# Uncertain states must never block — a probe blip stopping all collection is
# worse than a wasted sweep.
for state in ('ERROR', 'MODEL_UNAVAILABLE', 'RATE_LIMIT'):
    reset()
    _QUOTA_RESULTS[0] = [{'key': p, 'state': state} for p in
                         ('openai', 'gemini', 'anthropic', 'perplexity')]
    check(f'{state} on every provider does not block', GUARD.preflight_block() is None)

reset()
_QUOTA_RESULTS[0] = []
check('empty probe result does not block', GUARD.preflight_block() is None)

reset()


def _boom():
    raise RuntimeError('probe exploded')


sys.modules['weekly_sweep_guard_undertest.quota_monitor'].check_all_quotas = _boom
check('probe exception does not block', GUARD.preflight_block() is None)
sys.modules['weekly_sweep_guard_undertest.quota_monitor'].check_all_quotas = \
    lambda: _QUOTA_RESULTS[0]

reset(WEEKLY_SWEEP_PREFLIGHT_ENABLED=False)
_QUOTA_RESULTS[0] = [{'key': p, 'state': 'OUT_OF_CREDITS'} for p in
                     ('openai', 'gemini', 'anthropic', 'perplexity')]
check('preflight can be disabled', GUARD.preflight_block() is None)

# Only ENABLED_PLATFORMS matter — a dead provider nobody queries is irrelevant.
reset(ENABLED_PLATFORMS=['chatgpt'])
_QUOTA_RESULTS[0] = [
    {'key': 'openai', 'state': 'OK'},
    {'key': 'gemini', 'state': 'OUT_OF_CREDITS'},
]
check('disabled platform outage is ignored', GUARD.preflight_block() is None)

reset(ENABLED_PLATFORMS=['claude'])
_QUOTA_RESULTS[0] = [
    {'key': 'anthropic', 'state': 'OUT_OF_CREDITS'},
    {'key': 'openai', 'state': 'OK'},
]
blocked = GUARD.preflight_block()
check('platform->provider mapping resolves claude to anthropic',
      blocked is not None and blocked['reason'] == 'no_usable_provider', blocked)


# ---------------------------------------------------------------------------
print(f"\n{len(_PASS)} passed, {len(_FAIL)} failed")
if _FAIL:
    for name in _FAIL:
        print(f"  FAILED: {name}")
    sys.exit(1)
