"""Persist AI-referred GA4 traffic into `ga_ai_traffic_daily`.

Insights used to call GA4 on every page load and keep the answer only in a
15-minute cache, so none of its traffic figures existed in the database:
disconnecting the integration or passing GA4's retention window erased the
history, and the request path burned the property's hourly report quota. This
command moves that fetch off the request path and into a nightly job.

Two things it deliberately does NOT do naively:

* **The window is gap-aware.** A fixed "last 7 days" leaves a permanent hole
  whenever the job fails for longer than that — the missing days are never
  revisited. The window is widened to cover everything since the domain's last
  successful sync.
* **Rows are UPSERTed, not inserted.** GA4 restates recent days as late sessions
  land, so a day inside the rolling window is rewritten rather than duplicated.

Run nightly, e.g.::

    30 2 * * *  cd <backend> && <python> manage.py sync_ai_traffic

Options let you backfill (`--days 400`) or target one domain (`--domain-id`).
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from googleapiclient.discovery import build

from domains.models import Domain
from integrations.ai_platforms import AI_SOURCE_REGEX, resolve_platform
from integrations.models import GAAITrafficDaily, Integration
from integrations.google_oauth import get_credentials_from_integration

logger = logging.getLogger(__name__)

# GA4 restates the most recent days as late-arriving sessions are attributed, so
# always re-pull at least this much regardless of when the last sync ran.
MIN_ROLLING_DAYS = 7
# Ceiling for a single run, so a domain that has never synced (or has been dark
# for months) cannot ask GA4 for an unbounded range in one request.
MAX_WINDOW_DAYS = 400


class Command(BaseCommand):
    help = "Sync AI-referred GA4 traffic into ga_ai_traffic_daily (gap-aware rolling window)."

    def add_arguments(self, parser):
        parser.add_argument('--domain-id', type=int, default=None,
                            help="Sync a single domain instead of every connected one.")
        parser.add_argument('--days', type=int, default=None,
                            help="Force a fixed lookback (e.g. 400 to backfill) instead of the gap-aware window.")
        parser.add_argument('--dry-run', action='store_true',
                            help="Fetch and report, but write nothing.")

    def handle(self, *args, **options):
        integrations = Integration.objects.filter(type='google_analytics', status='active')
        if options['domain_id']:
            integrations = integrations.filter(domain_id=options['domain_id'])

        total_rows = 0
        for integration in integrations.select_related('domain'):
            try:
                rows = self._sync_one(integration, options)
                total_rows += rows
            except Exception as exc:  # one bad property must not stop the rest
                logger.exception("AI traffic sync failed for domain %s", integration.domain_id)
                self.stderr.write(f"  domain {integration.domain_id}: FAILED — {exc}")

        self.stdout.write(self.style.SUCCESS(f"Done. {total_rows} day/platform rows written."))

    # ------------------------------------------------------------------
    def _window(self, domain_id, forced_days):
        """(start, end) to pull. Ends YESTERDAY — GA4 treats today as incomplete
        and excludes it from its own 'last N days' presets, so including it would
        make our totals disagree with what the client sees in GA4."""
        end = timezone.localdate() - timedelta(days=1)
        if forced_days:
            return end - timedelta(days=forced_days - 1), end

        last = (GAAITrafficDaily.objects
                .filter(domain_id=domain_id)
                .order_by('-date')
                .values_list('date', flat=True)
                .first())
        if last is None:
            days = MAX_WINDOW_DAYS
        else:
            # Re-pull from the last stored day so restatements are picked up, and
            # widen to cover any gap left by a failed or skipped run.
            days = max(MIN_ROLLING_DAYS, (end - last).days + 1)
            days = min(days, MAX_WINDOW_DAYS)
        return end - timedelta(days=days - 1), end

    def _sync_one(self, integration, options):
        domain = integration.domain
        property_id = integration.provider_id or ''
        if not property_id:
            self.stdout.write(f"  domain {domain.id} ({domain.name}): no GA4 property selected, skipped")
            return 0
        if not property_id.startswith('properties/'):
            property_id = f'properties/{property_id}'

        credentials = get_credentials_from_integration(integration)
        if not credentials:
            self.stdout.write(f"  domain {domain.id} ({domain.name}): no valid credentials, skipped")
            return 0

        start, end = self._window(domain.id, options['days'])
        service = build('analyticsdata', 'v1beta', credentials=credentials)

        # Day x source, so both the combined row and the per-platform split come
        # from ONE report and therefore always reconcile with each other.
        response = service.properties().runReport(
            property=property_id,
            body={
                'dateRanges': [{'startDate': start.isoformat(), 'endDate': end.isoformat()}],
                'metrics': [
                    {'name': 'sessions'},
                    {'name': 'totalUsers'},
                    {'name': 'screenPageViews'},
                    {'name': 'conversions'},
                    {'name': 'averageSessionDuration'},
                ],
                'dimensions': [{'name': 'date'}, {'name': 'sessionSource'}],
                'dimensionFilter': {
                    'filter': {
                        'fieldName': 'sessionSource',
                        'stringFilter': {
                            'matchType': 'PARTIAL_REGEXP',
                            'value': AI_SOURCE_REGEX,
                            'caseSensitive': False,
                        }
                    }
                },
                'orderBys': [{'dimension': {'dimensionName': 'date'}}],
                'limit': 100000,
            }
        ).execute()

        property_timezone = self._property_timezone(credentials, property_id)
        rows = self._parse(response)
        if options['dry_run']:
            self.stdout.write(f"  domain {domain.id} ({domain.name}): {start}..{end} -> {len(rows)} rows (dry run)")
            return 0

        now = timezone.now()
        written = 0
        for (day, platform), m in rows.items():
            GAAITrafficDaily.objects.update_or_create(
                domain=domain, date=day, platform=platform,
                defaults={
                    'sessions': m['sessions'],
                    'users': m['users'],
                    'page_views': m['page_views'],
                    'conversions': m['conversions'],
                    'avg_duration': round(m['duration_weighted'] / m['sessions'], 2) if m['sessions'] else 0,
                    'property_id': property_id,
                    'property_timezone': property_timezone,
                    'synced_at': now,
                },
            )
            written += 1

        self.stdout.write(f"  domain {domain.id} ({domain.name}): {start}..{end} -> {written} rows")
        return written

    @staticmethod
    def _property_timezone(credentials, property_id):
        """GA4 buckets days in the property's timezone, which need not match the
        server's. The correlation chart joins these dates against snapshot dates,
        so the boundary is recorded rather than assumed.

        This is an ADMIN API field. The Data API's getMetadata returns the
        property's dimensions and metrics, not its settings, which is why an
        earlier attempt against it always came back empty.
        """
        try:
            admin = build('analyticsadmin', 'v1beta', credentials=credentials)
            prop = admin.properties().get(name=property_id).execute()
            return prop.get('timeZone', '') or ''
        except Exception as exc:
            logger.info("Could not read GA4 property timezone for %s: %s", property_id, exc)
            return ''

    @staticmethod
    def _parse(response):
        """GA rows -> {(date, platform): metrics}, plus a combined row per day.

        The combined row is summed from the same response as the per-platform
        rows, so the two can never disagree the way two separate GA4 queries can.
        """
        out = {}

        def bucket(key):
            return out.setdefault(key, {
                'sessions': 0, 'users': 0, 'page_views': 0,
                'conversions': 0, 'duration_weighted': 0.0,
            })

        for row in response.get('rows', []) or []:
            dims = [d.get('value', '') for d in row.get('dimensionValues', [])]
            mets = [m.get('value', '0') for m in row.get('metricValues', [])]
            if len(dims) < 2:
                continue
            raw_date, source = dims[0], dims[1]
            try:
                day = timezone.datetime.strptime(raw_date, '%Y%m%d').date()
            except ValueError:
                continue

            sessions = int(float(mets[0] or 0))
            users = int(float(mets[1] or 0))
            views = int(float(mets[2] or 0)) if len(mets) > 2 else 0
            conversions = int(float(mets[3] or 0)) if len(mets) > 3 else 0
            avg_dur = float(mets[4] or 0) if len(mets) > 4 else 0.0

            platform = resolve_platform(source) or source or 'unknown'
            for key in ((day, platform), (day, GAAITrafficDaily.ALL_PLATFORMS)):
                b = bucket(key)
                b['sessions'] += sessions
                b['users'] += users
                b['page_views'] += views
                b['conversions'] += conversions
                # Weighted so the combined row's average is a real mean across
                # sessions rather than an average of averages.
                b['duration_weighted'] += avg_dur * sessions

        return out
