"""
Test script for the LLM credit/quota alert gating.

Verifies that a depleted provider is emailed about exactly ONCE, that a single
bad probe can never raise an alert, and that the cooldown floor holds even when
the depleted set churns (which is what a duplicate scheduler used to cause).

quota_monitor only touches Django for `settings` and `timezone`, so this stubs
both and loads the module directly. That keeps the test runnable without a
database, a configured environment, or any network access.

Run:  python tests/standalone/engine/core/test_quota_monitor.py
"""
import importlib.util
import os
import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone as _tz
from pathlib import Path


ENGINE_CORE = Path(__file__).resolve().parents[4] / 'engine' / 'core'

_NOW = [datetime(2026, 7, 20, 6, 0, tzinfo=_tz.utc)]
_SENT = []
_PROBE_STATE = {'gemini': 'OK'}


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


class _RecordingMail:
    def send_report_email(self, **kwargs):
        _SENT.append(kwargs['subject'])
        return {'success': True}


def _load_quota_monitor():
    """Import quota_monitor with Django and requests stubbed out."""
    settings = _Settings()
    conf = types.ModuleType('django.conf')
    conf.settings = settings
    utils = types.ModuleType('django.utils')
    utils.timezone = _Clock
    sys.modules.update({
        'django': types.ModuleType('django'),
        'django.conf': conf,
        'django.utils': utils,
        'django.utils.timezone': _Clock,
        'requests': types.ModuleType('requests'),
    })
    mail = types.ModuleType('core.mailgun_email_service')
    mail.MailgunEmailService = _RecordingMail
    sys.modules['core.mailgun_email_service'] = mail

    path = ENGINE_CORE / 'quota_monitor.py'
    spec = importlib.util.spec_from_file_location('quota_monitor_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.check_all_quotas = lambda: [
        {'label': 'Google Gemini', 'key': key, 'key_set': True, 'state': state, 'detail': ''}
        for key, state in _PROBE_STATE.items()
    ]
    return module, settings


QM, SETTINGS = _load_quota_monitor()


def _configure(**overrides):
    """One-mail-per-outage configuration, matching production."""
    values = dict(
        QUOTA_ALERT_ENABLED=True,
        QUOTA_ALERT_RECIPIENTS=['ops@example.com'],
        QUOTA_ALERT_STATE_FILE=os.path.join(tempfile.mkdtemp(), 'quota_state.json'),
        QUOTA_ALERT_REPEAT_HOURS=0,          # reminders disabled
        QUOTA_ALERT_ON_RECOVERY=False,       # recovery mail disabled
        QUOTA_ALERT_CONFIRM_RUNS=2,
        QUOTA_ALERT_MIN_INTERVAL_MINUTES=60,
    )
    values.update(overrides)
    SETTINGS._apply(values)


def _run(label, advance_minutes=60):
    """Advance the clock, run one check, return how many mails it sent."""
    _NOW[0] += timedelta(minutes=advance_minutes)
    before = len(_SENT)
    result = QM.run_quota_check_and_alert()
    sent = len(_SENT) - before
    print(f"    {label:<32} depleted={str(result['depleted']):<12} mailed={sent}")
    return sent


def _reset(state='OK'):
    _SENT.clear()
    _PROBE_STATE['gemini'] = state


def test_depletion_alerts_exactly_once():
    print("  depletion is confirmed over 2 runs, then mailed exactly once")
    _configure()
    _reset('OK')
    assert _run('healthy') == 0
    _PROBE_STATE['gemini'] = 'OUT_OF_CREDITS'
    assert _run('depleted, 1st sighting') == 0, 'must not alert on one probe'
    assert _run('depleted, 2nd sighting') == 1, 'should alert once confirmed'
    assert _run('still depleted +1h') == 0, 'must not repeat'
    assert _run('still depleted +13h', 780) == 0, 'reminders are disabled'
    assert len(_SENT) == 1


def test_single_bad_probe_never_alerts():
    print("  a one-run blip never sends mail")
    _configure()
    _reset('OK')
    _run('healthy')
    _PROBE_STATE['gemini'] = 'OUT_OF_CREDITS'
    _run('transient blip')
    _PROBE_STATE['gemini'] = 'OK'
    _run('back to normal')
    assert len(_SENT) == 0


def test_recovery_is_silent_but_rearms():
    print("  recovery sends nothing but re-arms the next outage")
    _configure()
    _reset('OUT_OF_CREDITS')
    _run('outage 1, sighting 1')
    assert _run('outage 1, sighting 2') == 1
    _PROBE_STATE['gemini'] = 'OK'
    assert _run('topped up') == 0, 'recovery mail is disabled'
    _PROBE_STATE['gemini'] = 'OUT_OF_CREDITS'
    _run('outage 2, sighting 1')
    assert _run('outage 2, sighting 2') == 1, 'must alert on a new outage'
    assert len(_SENT) == 2


def test_cooldown_floor_blocks_a_flood():
    print("  cooldown suppresses rapid re-alerts even when state churns")
    _configure(QUOTA_ALERT_CONFIRM_RUNS=1)
    _reset('OUT_OF_CREDITS')
    assert _run('depleted') == 1
    _PROBE_STATE['gemini'] = 'OK'
    _run('recovered', advance_minutes=5)
    _PROBE_STATE['gemini'] = 'OUT_OF_CREDITS'
    assert _run('re-depleted 5m later', advance_minutes=5) == 0, 'cooldown must hold'


def test_reminder_still_works_when_enabled():
    print("  a positive REPEAT_HOURS still reminds (backward compatible)")
    _configure(QUOTA_ALERT_REPEAT_HOURS=12, QUOTA_ALERT_CONFIRM_RUNS=1)
    _reset('OUT_OF_CREDITS')
    assert _run('depleted') == 1
    assert _run('+1h') == 0
    assert _run('+13h', 780) == 1, 'reminder should fire once past REPEAT_HOURS'


def main():
    print("=" * 78)
    print("QUOTA ALERT GATING")
    print("=" * 78)
    for test in (
        test_depletion_alerts_exactly_once,
        test_single_bad_probe_never_alerts,
        test_recovery_is_silent_but_rearms,
        test_cooldown_floor_blocks_a_flood,
        test_reminder_still_works_when_enabled,
    ):
        test()
    print("=" * 78)
    print("ALL TESTS PASSED")


if __name__ == '__main__':
    main()
