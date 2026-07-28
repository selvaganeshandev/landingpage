"""
Test script for reconnect provider_id preservation.

Guards the fix for "some issue in connecting": pressing Connect again on an
already-connected domain used to wipe the selected property/site, which
silently stopped all syncing because every scheduler skips integrations with an
empty provider_id.

Pure logic — no Django, no database, no network.

Run:  python tests/standalone/backend/integrations/utils/test_reconnect.py
"""
import sys
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parents[5] / 'backend' / 'integrations' / 'utils'
sys.path.insert(0, str(SOURCE_DIR))

from reconnect import preserved_provider_id  # noqa: E402

GSC_SITES = [
    {'id': 'sc-domain:example.com', 'display_name': 'example.com'},
    {'id': 'https://shop.example.com/', 'display_name': 'shop.example.com'},
]
GA_PROPS = [
    {'id': 'properties/123456789', 'display_name': 'Main site'},
    {'id': 'properties/987654321', 'display_name': 'Blog'},
]


def test_keeps_selection_when_still_available():
    print("  keeps the selected site when the reconnected account still has it")
    assert preserved_provider_id('sc-domain:example.com', GSC_SITES) == 'sc-domain:example.com'
    assert preserved_provider_id('properties/123456789', GA_PROPS) == 'properties/123456789'


def test_clears_selection_when_account_no_longer_has_it():
    print("  clears the selection when reconnected with a different account")
    assert preserved_provider_id('sc-domain:other-company.com', GSC_SITES) == ''
    assert preserved_provider_id('properties/555555555', GA_PROPS) == ''


def test_preserves_when_the_list_could_not_be_fetched():
    """A transient Google outage must not destroy configuration. The caller has
    already flagged the integration disconnected, so the failure is surfaced."""
    print("  preserves the selection when the available list could not be fetched")
    assert preserved_provider_id('sc-domain:example.com', None) == 'sc-domain:example.com'
    assert preserved_provider_id('sc-domain:example.com', [], fetch_succeeded=False) == 'sc-domain:example.com'
    assert preserved_provider_id('sc-domain:example.com', GSC_SITES, fetch_succeeded=False) == 'sc-domain:example.com'


def test_first_time_connect_stays_empty():
    print("  a first-time connect still requires the user to select")
    assert preserved_provider_id('', GSC_SITES) == ''
    assert preserved_provider_id(None, GSC_SITES) == ''
    assert preserved_provider_id('', None) == ''


def test_tolerates_malformed_list_entries():
    print("  malformed entries in the available list do not raise")
    messy = [None, 'not-a-dict', {'no_id': 1}, {'id': 'sc-domain:example.com'}]
    assert preserved_provider_id('sc-domain:example.com', messy) == 'sc-domain:example.com'
    assert preserved_provider_id('sc-domain:missing.com', messy) == ''


def main():
    print("=" * 78)
    print("RECONNECT provider_id PRESERVATION")
    print("=" * 78)
    for test in (
        test_keeps_selection_when_still_available,
        test_clears_selection_when_account_no_longer_has_it,
        test_preserves_when_the_list_could_not_be_fetched,
        test_first_time_connect_stays_empty,
        test_tolerates_malformed_list_entries,
    ):
        test()
    print("=" * 78)
    print("ALL TESTS PASSED")


if __name__ == '__main__':
    main()
