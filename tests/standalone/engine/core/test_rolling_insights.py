"""
Test script for the daily rolling 30-day GA/GSC insight refresh.

Guards the fix for "report never updates after connecting": the rolling window
used to be built once at connect time and then frozen, because the hourly INIT
scheduler only picks up records that already exist and nothing re-INITed them.

This is READ-ONLY. `.delay` is stubbed, so no Celery task is dispatched and no
Google API call is made — it verifies which integrations WOULD be refreshed.

Run:  python tests/standalone/engine/core/test_rolling_insights.py
"""
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import django

ENGINE_ROOT = Path(__file__).resolve().parents[4] / 'engine'
sys.path.insert(0, str(ENGINE_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor_engine.settings')
django.setup()

from django.conf import settings  # noqa: E402

from core import processing_tasks as pt  # noqa: E402
from integrations.models import Integration  # noqa: E402

BEAT_KEY = 'rolling-insights-daily-refresh'
TASK_PATH = 'core.processing_tasks.schedule_all_rolling_insights_task'


class _Recorder:
    """Stands in for a Celery task so .delay() records instead of dispatching."""

    def __init__(self):
        self.ids = []

    def delay(self, integration_id):
        self.ids.append(integration_id)


class _QuerySet(list):
    """Small queryset double covering the scheduler's filter/exclude chain."""

    @staticmethod
    def _matches(item, key, expected):
        if key.endswith("__isnull"):
            field = key.removesuffix("__isnull")
            return (getattr(item, field) is None) is expected
        return getattr(item, key) == expected

    def filter(self, **lookups):
        return _QuerySet(
            item
            for item in self
            if all(self._matches(item, key, value) for key, value in lookups.items())
        )

    def exclude(self, **lookups):
        return _QuerySet(
            item
            for item in self
            if not all(self._matches(item, key, value) for key, value in lookups.items())
        )


_INTEGRATIONS = _QuerySet([
    SimpleNamespace(id=1, type="google_analytics", status="active", provider_id="ga-1"),
    SimpleNamespace(id=2, type="search_console", status="active", provider_id="gsc-1"),
    SimpleNamespace(id=3, type="google_analytics", status="inactive", provider_id="ga-2"),
    SimpleNamespace(id=4, type="search_console", status="active", provider_id=""),
    SimpleNamespace(id=5, type="google_analytics", status="active", provider_id=None),
    SimpleNamespace(id=6, type="search_console", status="inactive", provider_id="gsc-2"),
])


def _run_scheduler():
    ga_rec, gsc_rec = _Recorder(), _Recorder()
    with (
        patch.object(Integration, "objects", _INTEGRATIONS),
        patch.object(pt, "process_ga_insights_task", ga_rec),
        patch.object(pt, "process_gsc_insights_task", gsc_rec),
    ):
        result = pt.schedule_all_rolling_insights_task()
    return result, ga_rec.ids, gsc_rec.ids


def test_beat_schedule_registers_the_refresh():
    print("  the daily refresh is registered in the beat schedule")
    schedule = settings.CELERY_BEAT_SCHEDULE
    assert BEAT_KEY in schedule, f"{BEAT_KEY} missing from CELERY_BEAT_SCHEDULE"
    assert schedule[BEAT_KEY]['task'] == TASK_PATH, schedule[BEAT_KEY]['task']
    print(f"    {BEAT_KEY} -> {schedule[BEAT_KEY]['task']}")


def test_dispatches_every_eligible_integration():
    """An integration is eligible iff it is active AND has a property/site chosen.

    That is the same condition the hourly INIT scheduler filters on; if the two
    ever diverge, records get created that the scheduler refuses to process (or
    vice versa).
    """
    print("  dispatches exactly the active integrations that have a site selected")
    result, ga_ids, gsc_ids = _run_scheduler()
    print(f"    GA  dispatched={ga_ids} expected=[1]")
    print(f"    GSC dispatched={gsc_ids} expected=[2]")

    assert ga_ids == [1], 'GA dispatch set does not match eligible set'
    assert gsc_ids == [2], 'GSC dispatch set does not match eligible set'
    assert result == {'ga': 1, 'gsc': 1}, result


def test_never_dispatches_without_a_selected_site():
    """The regression that motivated claim E: a wiped provider_id must be skipped,
    not fetched — process_integration would immediately bail on it anyway."""
    print("  never dispatches an integration whose provider_id is empty/NULL")
    _, ga_ids, gsc_ids = _run_scheduler()
    bad = {4, 5}
    dispatched = set(ga_ids) | set(gsc_ids)
    overlap = dispatched & bad
    print(f"    unselected integrations={sorted(bad)} overlap={sorted(overlap) or 'none'}")
    assert not overlap, f"dispatched integrations with no site selected: {overlap}"


def test_inactive_integrations_are_skipped():
    print("  never dispatches an inactive integration")
    _, ga_ids, gsc_ids = _run_scheduler()
    inactive = {3, 6}
    dispatched = set(ga_ids) | set(gsc_ids)
    overlap = dispatched & inactive
    print(f"    inactive={sorted(inactive)} overlap={sorted(overlap) or 'none'}")
    assert not overlap, f"dispatched inactive integrations: {overlap}"


def main():
    print("=" * 78)
    print("ROLLING 30-DAY INSIGHT REFRESH")
    print("=" * 78)
    for test in (
        test_beat_schedule_registers_the_refresh,
        test_dispatches_every_eligible_integration,
        test_never_dispatches_without_a_selected_site,
        test_inactive_integrations_are_skipped,
    ):
        test()
    print("=" * 78)
    print("ALL TESTS PASSED")


if __name__ == '__main__':
    main()
