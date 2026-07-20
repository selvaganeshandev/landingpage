"""
Test script for the daily rolling 30-day GA/GSC insight refresh.

Guards the fix for "report never updates after connecting": the rolling window
used to be built once at connect time and then frozen, because the hourly INIT
scheduler only picks up records that already exist and nothing re-INITed them.

This is READ-ONLY. `.delay` is stubbed, so no Celery task is dispatched and no
Google API call is made — it verifies which integrations WOULD be refreshed.

Run:  python core/test_rolling_insights.py     (from the engine/ directory)
"""
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
    ga_rec, gsc_rec = _Recorder(), _Recorder()
    orig_ga, orig_gsc = pt.process_ga_insights_task, pt.process_gsc_insights_task
    pt.process_ga_insights_task, pt.process_gsc_insights_task = ga_rec, gsc_rec
    try:
        result = pt.schedule_all_rolling_insights_task()
    finally:
        pt.process_ga_insights_task, pt.process_gsc_insights_task = orig_ga, orig_gsc

    def eligible(kind):
        return set(
            Integration.objects
            .filter(type=kind, status='active', provider_id__isnull=False)
            .exclude(provider_id='')
            .values_list('id', flat=True)
        )

    expected_ga, expected_gsc = eligible('google_analytics'), eligible('search_console')
    print(f"    GA  dispatched={sorted(ga_rec.ids)}  expected={sorted(expected_ga)}")
    print(f"    GSC dispatched={sorted(gsc_rec.ids)} expected={sorted(expected_gsc)}")

    assert set(ga_rec.ids) == expected_ga, 'GA dispatch set does not match eligible set'
    assert set(gsc_rec.ids) == expected_gsc, 'GSC dispatch set does not match eligible set'
    assert result == {'ga': len(expected_ga), 'gsc': len(expected_gsc)}, result


def test_never_dispatches_without_a_selected_site():
    """The regression that motivated claim E: a wiped provider_id must be skipped,
    not fetched — process_integration would immediately bail on it anyway."""
    print("  never dispatches an integration whose provider_id is empty/NULL")
    ga_rec, gsc_rec = _Recorder(), _Recorder()
    orig_ga, orig_gsc = pt.process_ga_insights_task, pt.process_gsc_insights_task
    pt.process_ga_insights_task, pt.process_gsc_insights_task = ga_rec, gsc_rec
    try:
        pt.schedule_all_rolling_insights_task()
    finally:
        pt.process_ga_insights_task, pt.process_gsc_insights_task = orig_ga, orig_gsc

    bad = set(
        Integration.objects
        .filter(provider_id__in=['', None])
        .values_list('id', flat=True)
    )
    dispatched = set(ga_rec.ids) | set(gsc_rec.ids)
    overlap = dispatched & bad
    print(f"    unselected integrations={sorted(bad) or 'none'}  overlap={sorted(overlap) or 'none'}")
    assert not overlap, f"dispatched integrations with no site selected: {overlap}"


def test_inactive_integrations_are_skipped():
    print("  never dispatches an inactive integration")
    ga_rec, gsc_rec = _Recorder(), _Recorder()
    orig_ga, orig_gsc = pt.process_ga_insights_task, pt.process_gsc_insights_task
    pt.process_ga_insights_task, pt.process_gsc_insights_task = ga_rec, gsc_rec
    try:
        pt.schedule_all_rolling_insights_task()
    finally:
        pt.process_ga_insights_task, pt.process_gsc_insights_task = orig_ga, orig_gsc

    inactive = set(
        Integration.objects.exclude(status='active').values_list('id', flat=True)
    )
    dispatched = set(ga_rec.ids) | set(gsc_rec.ids)
    overlap = dispatched & inactive
    print(f"    inactive={sorted(inactive) or 'none'}  overlap={sorted(overlap) or 'none'}")
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
