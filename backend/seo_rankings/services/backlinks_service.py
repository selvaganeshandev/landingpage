"""
Backlink profile orchestration — backend side.

The backend does not call DataForSEO. A full pull is 10+ sequential HTTP
requests and would hold a gunicorn worker for a minute or more, so the actual
fetching lives in ``engine/core/backlinks_processor.py`` on the `seo` queue.
This module owns the three things that must NOT live in a worker:

  * the monthly refresh guard, which is a spending control and belongs in front
    of the dispatch, not inside it;
  * snapshot creation, so the UI has a row to poll the instant the button is
    pressed rather than after the queue picks the job up;
  * the read helpers the page renders from.

Cost context for anyone tempted to loosen the guard: one uncapped pull of
havells.com is $11.58 (149,899 backlinks at $0.024/request + $0.000036/row).
The engine caps detail rows at 1,000 per list, which brings a fetch to ~$0.29.
"""
import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# A refresh is allowed once a month. A constant rather than a setting because
# the UI quotes the resulting date back to the user and support needs one
# answer to "when can I refresh", not one per environment.
REFRESH_INTERVAL_DAYS = getattr(settings, "BACKLINK_REFRESH_INTERVAL_DAYS", 30)

# A snapshot left in PEND/RUN longer than this had its worker die under it.
STALE_RUNNING_MINUTES = 30

ENGINE_TIMEOUT = 15


class RefreshTooSoon(Exception):
    """Raised when a refresh is requested inside the monthly window.

    Carries the date the UI must display, so the view never recomputes it.
    """

    def __init__(self, next_allowed_at):
        self.next_allowed_at = next_allowed_at
        super().__init__(
            f"Backlinks can be refreshed once a month. "
            f"Next refresh available on {next_allowed_at:%d %b %Y}."
        )


class FetchAlreadyRunning(Exception):
    """A pull for this domain is already in flight."""

    def __init__(self, snapshot):
        self.snapshot = snapshot
        super().__init__("A backlink fetch is already running for this project.")


class FirstFetchDisabled(Exception):
    """First-ever pull for a project is switched off.

    Every project that has never been fetched is a brand-new charge against the
    prepaid balance, and there are ~45 of them. The monthly guard only limits
    projects that already have data; this closes the other side.
    """

    def __init__(self):
        super().__init__(
            "Fetching backlinks for a new project is temporarily switched off. "
            "Projects that already have backlink data can still be refreshed."
        )


def first_fetch_enabled() -> bool:
    """Whether a project with no existing data may be fetched for the first time.

    Off by default and flipped with BACKLINK_FIRST_FETCH_ENABLED in .env, so it
    can be opened for one deliberate pull and closed again without a deploy.
    """
    return bool(getattr(settings, "BACKLINK_FIRST_FETCH_ENABLED", False))


def has_data(domain) -> bool:
    return latest_snapshot(domain) is not None


def next_refresh_at(completed_at):
    return completed_at + timedelta(days=REFRESH_INTERVAL_DAYS)


def latest_snapshot(domain):
    """The most recent completed snapshot, or None if never fetched."""
    from ..models import SeoBacklinkSnapshot

    return (
        SeoBacklinkSnapshot.objects
        .filter(domain=domain, status='DONE')
        .order_by('-completed_at')
        .first()
    )


def running_snapshot(domain):
    """An in-flight fetch, if one is genuinely still running.

    Anything older than STALE_RUNNING_MINUTES is failed out first, so a crashed
    worker cannot leave the button disabled forever.
    """
    from ..models import SeoBacklinkSnapshot

    cutoff = timezone.now() - timedelta(minutes=STALE_RUNNING_MINUTES)
    qs = SeoBacklinkSnapshot.objects.filter(domain=domain, status__in=['PEND', 'RUN'])
    qs.filter(started_at__lt=cutoff).update(
        status='FAIL',
        error_message='Fetch did not complete — worker stopped.',
        completed_at=timezone.now(),
    )
    return qs.filter(started_at__gte=cutoff).order_by('-started_at').first()


def last_failed_snapshot(domain):
    """The most recent failure, used to surface the error on the page."""
    from ..models import SeoBacklinkSnapshot

    return (
        SeoBacklinkSnapshot.objects
        .filter(domain=domain, status='FAIL')
        .order_by('-completed_at', '-started_at')
        .first()
    )


def refresh_guard(domain, *, force: bool = False):
    """Raise RefreshTooSoon unless the monthly window has elapsed.

    `force` is for staff/support only and must never be reachable from the
    customer-facing button — it spends money with no cooldown.
    """
    if force:
        return
    last = latest_snapshot(domain)
    if last and last.next_refresh_allowed_at and timezone.now() < last.next_refresh_allowed_at:
        raise RefreshTooSoon(last.next_refresh_allowed_at)


def start_fetch(domain, *, account=None, force: bool = False):
    """Create a PEND snapshot and dispatch it to the engine.

    Returns the snapshot. Raises RefreshTooSoon inside the monthly window, or
    FetchAlreadyRunning if one is in flight.
    """
    from ..models import SeoBacklinkSnapshot

    in_flight = running_snapshot(domain)
    if in_flight:
        raise FetchAlreadyRunning(in_flight)

    # Enforced here rather than only in the UI — hiding the button does not stop
    # a POST, and this is the control that actually protects the balance.
    if not force and not has_data(domain) and not first_fetch_enabled():
        raise FirstFetchDisabled()

    refresh_guard(domain, force=force)

    snapshot = SeoBacklinkSnapshot.objects.create(
        domain=domain, status='PEND', requested_by=account,
    )

    engine_url = getattr(settings, 'ENGINE_API_URL', 'http://localhost:8001').rstrip('/')
    try:
        resp = requests.post(
            f'{engine_url}/api/seo/fetch-backlinks/',
            json={'snapshot_id': snapshot.id},
            timeout=ENGINE_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        # The row exists but nothing will ever pick it up, so fail it now
        # rather than leaving the UI spinning for STALE_RUNNING_MINUTES.
        snapshot.status = 'FAIL'
        snapshot.error_message = f"Could not reach the processing engine: {exc}"
        snapshot.completed_at = timezone.now()
        snapshot.save(update_fields=['status', 'error_message', 'completed_at'])
        logger.error("[BL] Engine dispatch failed for domain %s: %s", domain.pk, exc)
        raise

    return snapshot
