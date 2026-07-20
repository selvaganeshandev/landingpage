"""
Test script for Google OAuth credential expiry parsing and token persistence.

Guards the fix for tokens silently going stale: the stored `expiry` was written
on connect but never read back, so google-auth saw expiry=None, treated the
access token as valid forever, and never refreshed proactively. Any refreshed
token was also thrown away at the end of the process instead of being saved.

No Django and no network — the Google client library is the only import, and the
integration is a plain stub.

Run:  python integrations/test_google_oauth_helper.py
"""
import os
import sys
from datetime import datetime, timedelta, timezone as dt_timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.google_oauth_helper import (  # noqa: E402
    get_credentials_from_integration,
    parse_stored_expiry,
    persist_refreshed_credentials,
)


class _StubIntegration:
    id = 42

    def __init__(self, credentials):
        self.credentials = credentials
        self.saved_fields = None

    def save(self, update_fields=None):
        self.saved_fields = update_fields


class _StubCredentials:
    def __init__(self, token, expiry):
        self.token = token
        self.expiry = expiry


def test_parses_naive_and_aware_expiry():
    print("  stored expiry is parsed back to naive UTC for google-auth")
    naive = parse_stored_expiry('2026-07-20T06:30:00')
    assert naive == datetime(2026, 7, 20, 6, 30), naive
    assert naive.tzinfo is None

    # +05:30 -> 01:00 UTC, and google-auth compares against utcnow(), so the
    # result must be naive or every comparison raises TypeError.
    aware = parse_stored_expiry('2026-07-20T06:30:00+05:30')
    assert aware == datetime(2026, 7, 20, 1, 0), aware
    assert aware.tzinfo is None


def test_missing_or_broken_expiry_is_tolerated():
    print("  a missing or malformed expiry degrades to None, never raises")
    for bad in (None, '', 'not-a-date', 12345):
        assert parse_stored_expiry(bad) is None, bad


def test_expiry_is_actually_applied_to_credentials():
    """The bug: expiry was stored but never passed to Credentials, so .expired
    was always False and the token was never refreshed before use."""
    print("  credentials carry the stored expiry, so .expired is meaningful")
    past = (datetime.now(dt_timezone.utc) - timedelta(hours=2)).replace(tzinfo=None)
    integration = _StubIntegration({
        'token': 'stale-token',
        'refresh_token': None,          # no refresh -> no network attempted
        'client_id': 'cid',
        'client_secret': 'secret',
        'expiry': past.isoformat(),
    })
    creds = get_credentials_from_integration(integration)
    assert creds.expiry == past, (creds.expiry, past)
    assert creds.expired is True, 'an expired stored token must report expired'

    future = (datetime.now(dt_timezone.utc) + timedelta(hours=2)).replace(tzinfo=None)
    integration.credentials['expiry'] = future.isoformat()
    creds = get_credentials_from_integration(integration)
    assert creds.expired is False, 'a live token must not report expired'


def test_no_credentials_returns_none():
    print("  an integration with no stored credentials yields None")
    assert get_credentials_from_integration(_StubIntegration(None)) is None
    assert get_credentials_from_integration(_StubIntegration({})) is None


def test_persist_writes_token_and_expiry_only():
    print("  persisting writes only the credentials field, keeping other keys")
    expiry = datetime(2026, 7, 20, 9, 0)
    integration = _StubIntegration({
        'token': 'old', 'refresh_token': 'keep-me',
        'available_sites': [{'id': 'sc-domain:example.com'}],
        'expiry': '2026-07-20T06:00:00',
    })
    persist_refreshed_credentials(integration, _StubCredentials('new-token', expiry))

    assert integration.credentials['token'] == 'new-token'
    assert integration.credentials['expiry'] == expiry.isoformat()
    # Unrelated keys must survive — available_sites drives the reconnect
    # preservation logic and the site picker.
    assert integration.credentials['refresh_token'] == 'keep-me'
    assert integration.credentials['available_sites'] == [{'id': 'sc-domain:example.com'}]
    assert integration.saved_fields == ['credentials'], integration.saved_fields


def test_persist_failure_does_not_raise():
    """A failed write must not break the fetch that triggered it."""
    print("  a failed save is swallowed so the in-flight fetch still proceeds")

    class _Exploding(_StubIntegration):
        def save(self, update_fields=None):
            raise RuntimeError('database is down')

    integration = _Exploding({'token': 'old'})
    persist_refreshed_credentials(integration, _StubCredentials('new', None))


def main():
    print("=" * 78)
    print("GOOGLE OAUTH TOKEN EXPIRY + PERSISTENCE")
    print("=" * 78)
    for test in (
        test_parses_naive_and_aware_expiry,
        test_missing_or_broken_expiry_is_tolerated,
        test_expiry_is_actually_applied_to_credentials,
        test_no_credentials_returns_none,
        test_persist_writes_token_and_expiry_only,
        test_persist_failure_does_not_raise,
    ):
        test()
    print("=" * 78)
    print("ALL TESTS PASSED")


if __name__ == '__main__':
    main()
