"""
Test script for partial-failure reporting in the GA/GSC insight processors.

Guards the fix for "connected, but the report is empty and nothing says why":
each section fetch swallows its own exception and returns []/{}, so a section
that ERRORED used to be indistinguishable from a section with genuinely no
traffic — both were saved as a clean COMP.

Now the failed sections are collected and named in track_message, and an insight
where EVERY section failed is marked FAIL instead of an empty COMP.

No network and no database: the API client, the credentials helper and the
section fetchers are replaced with stubs, and the insight is a plain object.

Run:  python core/test_insight_partial_failures.py     (from the engine/ directory)
"""
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor_engine.settings')
django.setup()

from datetime import date, timedelta  # noqa: E402

from core import gsc_insights_processor as gsc_mod  # noqa: E402
from core import ga_insights_processor as ga_mod  # noqa: E402


class _StubInsight:
    """Accepts any attribute assignment and a no-op save()."""

    def save(self):
        pass


class _StubIntegration:
    provider_id = 'sc-domain:example.com'


class _ExplodingService:
    """Any attribute access chain ends in a call that raises."""

    def __getattr__(self, _name):
        return self

    def __call__(self, *args, **kwargs):
        return self

    def execute(self):
        raise RuntimeError('simulated Google API failure')


def _patch(module, names, values):
    originals = {n: getattr(module, n) for n in names}
    for n, v in zip(names, values):
        setattr(module, n, v)
    return originals


def _restore(module, originals):
    for n, v in originals.items():
        setattr(module, n, v)


# ---------------------------------------------------------------------------
# Pure message formatting
# ---------------------------------------------------------------------------
def test_completion_message():
    print("  track_message names the failed sections, or says success")
    for mod in (gsc_mod, ga_mod):
        assert mod._completion_message(None) == 'Successfully processed'
        assert mod._completion_message([]) == 'Successfully processed'
        msg = mod._completion_message(['top queries', 'device breakdown'])
        assert msg == 'Partially processed - could not fetch: top queries, device breakdown', msg


# ---------------------------------------------------------------------------
# Each section records its own failure
# ---------------------------------------------------------------------------
def test_every_gsc_section_records_its_failure():
    print("  every GSC section appends its name when the API call raises")
    p = gsc_mod.GSCInsightsProcessor()
    svc, start, end = _ExplodingService(), date(2026, 6, 1), date(2026, 6, 30)
    expected = ['overall metrics', 'top queries', 'top pages', 'device breakdown', 'country breakdown']
    calls = [p._fetch_overall_metrics, p._fetch_top_queries, p._fetch_top_pages,
             p._fetch_device_breakdown, p._fetch_country_breakdown]
    for fn, label in zip(calls, expected):
        failures = []
        result = fn(svc, 'sc-domain:example.com', start, end, failures=failures)
        assert failures == [label], f"{fn.__name__} recorded {failures}, expected [{label!r}]"
        assert not result, f"{fn.__name__} should return an empty value on failure, got {result!r}"
    print(f"    recorded: {expected}")
    assert len(expected) == gsc_mod.TOTAL_GSC_SECTIONS, (
        f"TOTAL_GSC_SECTIONS={gsc_mod.TOTAL_GSC_SECTIONS} but {len(expected)} sections are fetched"
    )


def test_every_ga_section_records_its_failure():
    print("  every GA section appends its name when the API call raises")
    p = ga_mod.GAInsightsProcessor()
    svc, start, end = _ExplodingService(), date(2026, 6, 1), date(2026, 6, 30)
    expected = ['overall metrics', 'platform breakdown', 'device breakdown',
                'geographic breakdown', 'landing pages']
    calls = [p._fetch_overall_metrics, p._fetch_platform_breakdown, p._fetch_device_breakdown,
             p._fetch_geographic_breakdown, p._fetch_landing_pages]
    for fn, label in zip(calls, expected):
        failures = []
        result = fn(svc, 'properties/123', start, end, failures=failures)
        assert failures == [label], f"{fn.__name__} recorded {failures}, expected [{label!r}]"
        assert not result, f"{fn.__name__} should return an empty value on failure, got {result!r}"
    print(f"    recorded: {expected}")
    assert len(expected) == ga_mod.TOTAL_GA_SECTIONS, (
        f"TOTAL_GA_SECTIONS={ga_mod.TOTAL_GA_SECTIONS} but {len(expected)} sections are fetched"
    )


# ---------------------------------------------------------------------------
# Orchestrator: partial -> COMP with names, total -> FAIL
# ---------------------------------------------------------------------------
def _run_gsc_fetch(failing_sections):
    """Run _fetch_gsc_data with the section fetchers stubbed to fail selectively."""
    p = gsc_mod.GSCInsightsProcessor()
    names = ['_fetch_overall_metrics', '_fetch_top_queries', '_fetch_top_pages',
             '_fetch_device_breakdown', '_fetch_country_breakdown']
    labels = ['overall metrics', 'top queries', 'top pages', 'device breakdown', 'country breakdown']

    def make(label, empty):
        def stub(*args, **kwargs):
            failures = kwargs.get('failures')
            if label in failing_sections and failures is not None:
                failures.append(label)
            return empty
        return stub

    for name, label in zip(names, labels):
        setattr(p, name, make(label, {} if 'metrics' in name or 'breakdown' in name else []))

    originals = _patch(
        gsc_mod,
        ['get_credentials_from_integration', 'build'],
        [lambda integration: object(), lambda *a, **k: _ExplodingService()],
    )
    try:
        return p._fetch_gsc_data(_StubInsight(), _StubIntegration(),
                                 date.today() - timedelta(days=30), date.today())
    finally:
        _restore(gsc_mod, originals)


def test_partial_failure_still_completes_and_is_named():
    print("  a partial failure still COMPLETES but names the broken sections")
    result = _run_gsc_fetch({'top queries', 'country breakdown'})
    print(f"    result: {result}")
    assert result['success'] is True, result
    assert result['partial_failures'] == ['top queries', 'country breakdown'], result
    msg = gsc_mod._completion_message(result['partial_failures'])
    assert msg == 'Partially processed - could not fetch: top queries, country breakdown', msg


def test_total_failure_is_not_reported_as_complete():
    print("  when EVERY section fails the insight fails instead of completing empty")
    everything = {'overall metrics', 'top queries', 'top pages',
                  'device breakdown', 'country breakdown'}
    result = _run_gsc_fetch(everything)
    print(f"    result: {result}")
    assert result['success'] is False, 'a total failure must not be stored as COMP'
    assert 'All GSC sections failed' in result['error'], result


def test_clean_run_reports_no_failures():
    print("  a clean run reports no partial failures")
    result = _run_gsc_fetch(set())
    assert result['success'] is True, result
    assert result['partial_failures'] == [], result
    assert gsc_mod._completion_message(result['partial_failures']) == 'Successfully processed'


def main():
    print("=" * 78)
    print("INSIGHT PARTIAL-FAILURE REPORTING")
    print("=" * 78)
    for test in (
        test_completion_message,
        test_every_gsc_section_records_its_failure,
        test_every_ga_section_records_its_failure,
        test_partial_failure_still_completes_and_is_named,
        test_total_failure_is_not_reported_as_complete,
        test_clean_run_reports_no_failures,
    ):
        test()
    print("=" * 78)
    print("ALL TESTS PASSED")


if __name__ == '__main__':
    main()
