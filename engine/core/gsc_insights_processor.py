"""
GSC Insights Processor: Fetches and stores Google Search Console traffic data
"""
import logging
from collections import defaultdict
from typing import Dict, Any
from datetime import datetime, timedelta, date
import calendar
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone

# Import from engine's integrations app
from integrations.models import Integration, GSCTrafficInsight
from shared_models.models import Domain
from shared_models.seo_models import SeoKeywordRank
from integrations.google_oauth_helper import get_credentials_from_integration
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Independent sections fetched per insight: overall metrics, top queries, top
# pages, device breakdown, country breakdown. If every one of them fails there
# is no data at all, so the insight is marked FAIL rather than an empty COMP.
TOTAL_GSC_SECTIONS = 5

# Keyword-level sync window. Search Console finalises data on a ~2-3 day lag, so
# it reads 7 complete days ending 3 days back — the window the keyword table's
# CLKS/IMPS tooltip describes ("last 7 days").
GSC_KEYWORD_WINDOW_DAYS = 7
GSC_KEYWORD_LAG_DAYS = 3
GSC_MAX_PAGE_ROWS = 25000  # Search Analytics API maximum rowLimit

# Search Console filters by ISO 3166-1 alpha-3; keyword rows store the alpha-2
# code the rank crawl uses. A code missing here is skipped (and reported)
# rather than synced without a country filter, which would show worldwide
# numbers under a single-country keyword.
GSC_COUNTRY_CODES = {
    'in': 'ind', 'us': 'usa', 'ae': 'are', 'sa': 'sau', 'kw': 'kwt', 'qa': 'qat',
    'om': 'omn', 'bh': 'bhr', 'sg': 'sgp', 'gb': 'gbr', 'uk': 'gbr', 'au': 'aus',
    'ca': 'can', 'nz': 'nzl', 'ie': 'irl', 'de': 'deu', 'fr': 'fra', 'es': 'esp',
    'it': 'ita', 'nl': 'nld', 'my': 'mys', 'id': 'idn', 'ph': 'phl', 'pk': 'pak',
    'bd': 'bgd', 'lk': 'lka', 'np': 'npl', 'za': 'zaf', 'eg': 'egy', 'jo': 'jor',
}


def _normalise_query(text) -> str:
    """Match key for a keyword or GSC query: lower-cased, whitespace collapsed."""
    return ' '.join((text or '').lower().split())


def _completion_message(partial_failures) -> str:
    """track_message for a completed insight, naming any sections that failed."""
    if not partial_failures:
        return 'Successfully processed'
    return 'Partially processed - could not fetch: ' + ', '.join(partial_failures)


class GSCInsightsProcessor:
    """
    Processor for fetching and storing Google Search Console traffic insights
    """
    
    def process_insight(self, insight_id: int) -> Dict[str, Any]:
        """
        Process a specific GSC insight record
        
        Args:
            insight_id: ID of the GSCTrafficInsight record to process
            
        Returns:
            Dict with processing results
        """
        try:
            with transaction.atomic():
                insight = GSCTrafficInsight.objects.select_for_update().get(id=insight_id)
                
                # Validate insight is in INIT status
                if insight.track_status != 'INIT':
                    logger.warning(f"Insight {insight_id} is in status {insight.track_status}, expected INIT")
                    return {
                        'success': False,
                        'error': f'Insight is in status {insight.track_status}, expected INIT'
                    }
                
                # Get integration
                integration = insight.integration
                
                # Validate integration
                if integration.status != 'active':
                    logger.warning(f"Integration {integration.id} is not active")
                    insight.track_status = 'FAIL'
                    insight.track_message = f'Integration is not active (status: {integration.status})'
                    insight.save()
                    return {
                        'success': False,
                        'error': 'Integration is not active'
                    }
                
                if not integration.provider_id or integration.provider_id == '':
                    logger.warning(f"Integration {integration.id} has no provider_id set")
                    insight.track_status = 'FAIL'
                    insight.track_message = 'No site selected for this integration'
                    insight.save()
                    return {
                        'success': False,
                        'error': 'No site selected for this integration'
                    }
                
                # Check if same integration is already processing
                if GSCTrafficInsight.objects.filter(
                    integration=integration,
                    track_status='PROC'
                ).exclude(id=insight_id).exists():
                    logger.info(f"Integration {integration.id} already has another insight processing")
                    return {
                        'success': False,
                        'error': 'Another insight for this integration is already processing'
                    }
                
                # Mark as processing
                insight.track_status = 'PROC'
                insight.track_message = 'Fetching data from Google Search Console'
                insight.save()
            
            # Fetch data from GSC
            result = self._fetch_gsc_data(insight, integration, insight.start_date, insight.end_date)
            
            if result['success']:
                with transaction.atomic():
                    insight = GSCTrafficInsight.objects.select_for_update().get(id=insight.id)
                    insight.track_status = 'COMP'
                    insight.track_message = _completion_message(result.get('partial_failures'))
                    insight.save()
                
                logger.info(f"Successfully processed GSC insight {insight_id}")
                return {
                    'success': True,
                    'insight_id': insight.id,
                    'message': 'GSC insights processed successfully'
                }
            else:
                with transaction.atomic():
                    insight = GSCTrafficInsight.objects.select_for_update().get(id=insight.id)
                    insight.track_status = 'FAIL'
                    insight.track_message = result.get('error', 'Unknown error')
                    insight.save()
                
                return result
                
        except GSCTrafficInsight.DoesNotExist:
            logger.error(f"GSC insight {insight_id} not found")
            return {
                'success': False,
                'error': 'Insight not found'
            }
        except Exception as e:
            logger.error(f"Error processing GSC insight {insight_id}: {str(e)}", exc_info=True)
            # Try to mark as failed
            try:
                with transaction.atomic():
                    insight = GSCTrafficInsight.objects.select_for_update().get(id=insight_id)
                    insight.track_status = 'FAIL'
                    insight.track_message = str(e)
                    insight.save()
            except:
                pass
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_integration(self, integration_id: int, days_back: int = 30) -> Dict[str, Any]:
        """
        Process GSC insights for a specific integration
        
        Args:
            integration_id: ID of the integration to process
            days_back: Number of days to look back (default: 30)
            
        Returns:
            Dict with processing results
        """
        try:
            with transaction.atomic():
                integration = Integration.objects.select_for_update().get(
                    id=integration_id,
                    type='search_console',
                    status='active'
                )
                
                if not integration.provider_id or integration.provider_id == '':
                    logger.warning(f"Integration {integration_id} has no provider_id set")
                    return {
                        'success': False,
                        'error': 'No site selected for this integration'
                    }
                
                # Check if already processing
                if integration.gsc_insights.filter(track_status='PROC').exists():
                    logger.info(f"Integration {integration_id} already has processing insight")
                    return {
                        'success': False,
                        'error': 'Already processing'
                    }
                
                # Calculate date range
                end_date = date.today()
                start_date = end_date - timedelta(days=days_back)
                
                # Create or get insight record
                insight, created = GSCTrafficInsight.objects.get_or_create(
                    integration=integration,
                    domain=integration.domain,
                    start_date=start_date,
                    end_date=end_date,
                    defaults={
                        'track_status': 'INIT',
                    }
                )
                
                if insight.track_status == 'COMP':
                    logger.info(f"Insight {insight.id} already completed, resetting for reprocessing")
                    insight.track_status = 'INIT'
                    insight.save()
                
                if insight.track_status not in ['INIT', 'FAIL']:
                    logger.warning(f"Insight {insight.id} is in status {insight.track_status}, skipping")
                    return {
                        'success': False,
                        'error': f'Insight already in status {insight.track_status}'
                    }
                
                # Mark as processing
                insight.track_status = 'PROC'
                insight.track_message = 'Fetching data from Google Search Console'
                insight.save()
            
            # Fetch data from GSC
            result = self._fetch_gsc_data(insight, integration, start_date, end_date)
            
            if result['success']:
                with transaction.atomic():
                    insight = GSCTrafficInsight.objects.select_for_update().get(id=insight.id)
                    insight.track_status = 'COMP'
                    insight.track_message = _completion_message(result.get('partial_failures'))
                    insight.save()
                
                logger.info(f"Successfully processed GSC insights for integration {integration_id}")
                return {
                    'success': True,
                    'insight_id': insight.id,
                    'message': 'GSC insights processed successfully'
                }
            else:
                with transaction.atomic():
                    insight = GSCTrafficInsight.objects.select_for_update().get(id=insight.id)
                    insight.track_status = 'FAIL'
                    insight.track_message = result.get('error', 'Unknown error')
                    insight.save()
                
                return result
                
        except Integration.DoesNotExist:
            logger.error(f"Integration {integration_id} not found")
            return {
                'success': False,
                'error': 'Integration not found'
            }
        except Exception as e:
            logger.error(f"Error processing GSC insights for integration {integration_id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_monthly_insights(self, integration_id: int) -> Dict[str, Any]:
        """
        Create/update 3 calendar-month-aligned GSC insight records for MoM and YoY.

        Records created:
          current_month  — Apr 1 → Apr 30  (incomplete, prorated in API)
          prev_month     — Mar 1 → Mar 31  (complete)
          yoy_month      — Apr 1 2025 → Apr 30 2025 (complete)

        Uses get_or_create on (integration, start_date, end_date) so the same
        record is updated each day within the month (no duplicates).
        The existing scheduler picks up INIT records and processes them normally.
        """
        try:
            integration = Integration.objects.get(
                id=integration_id, type='search_console', status='active'
            )

            if not integration.provider_id or integration.provider_id == '':
                return {'success': False, 'error': 'No site selected for this integration'}

            today = date.today()
            month_start = today.replace(day=1)
            month_last_day = calendar.monthrange(today.year, today.month)[1]
            month_end = today.replace(day=month_last_day)

            # Previous month
            if today.month == 1:
                prev_year, prev_month = today.year - 1, 12
            else:
                prev_year, prev_month = today.year, today.month - 1
            prev_start = date(prev_year, prev_month, 1)
            prev_last_day = calendar.monthrange(prev_year, prev_month)[1]
            prev_end = date(prev_year, prev_month, prev_last_day)

            # Same month last year
            yoy_year = today.year - 1
            yoy_last_day = calendar.monthrange(yoy_year, today.month)[1]
            yoy_start = date(yoy_year, today.month, 1)
            yoy_end = date(yoy_year, today.month, yoy_last_day)

            periods = [
                ('current_month', month_start, month_end),
                ('prev_month',    prev_start,  prev_end),
                ('yoy_month',     yoy_start,   yoy_end),
            ]

            created_ids = []
            for period_type, start, end in periods:
                insight, created = GSCTrafficInsight.objects.get_or_create(
                    integration=integration,
                    start_date=start,
                    end_date=end,
                    defaults={
                        'domain': integration.domain,
                        'track_status': 'INIT',
                        'period_type': period_type,
                    }
                )
                if not created:
                    # Re-fetch daily: reset to INIT and update period_type label
                    GSCTrafficInsight.objects.filter(id=insight.id).update(
                        period_type=period_type,
                        track_status='INIT',
                        track_message=None,
                    )
                    logger.info(
                        f"GSC monthly insight reset to INIT: integration={integration_id} "
                        f"period={period_type} ({start}→{end})"
                    )
                else:
                    logger.info(
                        f"GSC monthly insight created: integration={integration_id} "
                        f"period={period_type} ({start}→{end})"
                    )
                created_ids.append(insight.id)

            return {
                'success': True,
                'insight_ids': created_ids,
                'message': f'Scheduled {len(created_ids)} monthly GSC insight records'
            }

        except Integration.DoesNotExist:
            return {'success': False, 'error': f'Integration {integration_id} not found or not active'}
        except Exception as e:
            logger.error(f"Error scheduling monthly GSC insights for integration {integration_id}: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def sync_keyword_metrics(self, integration_id: int) -> Dict[str, Any]:
        """
        Copy per-keyword clicks and impressions from Search Console onto the
        domain's tracked SEO keywords (SeoKeywordRank.gsc_clicks/gsc_impressions).

        Nothing wrote those columns before — only the one-off Rankmax import —
        so the keyword table showed 0 for every domain even with GSC connected.
        The stored insights keep only the top 100 queries, which miss most
        tracked keywords, so this pulls every query in the window instead.

        Matching is exact on the normalised text, per keyword country. Devices
        are combined, so a keyword's desktop and mobile rows show the same
        figures. A keyword with no matching query had no impressions and gets 0;
        a country whose fetch failed is left untouched.
        """
        try:
            integration = Integration.objects.get(
                id=integration_id, type='search_console', status='active'
            )
        except Integration.DoesNotExist:
            return {'success': False, 'error': f'Integration {integration_id} not found or not active'}

        # Report-only secondary integrations have no domain and no tracked keywords.
        if not integration.provider_id or not integration.domain_id:
            return {'success': False, 'error': 'No site or domain for this integration'}

        rows = list(
            SeoKeywordRank.objects.filter(domain_id=integration.domain_id)
            .select_related('keyword')
            .only('id', 'isocode', 'gsc_clicks', 'gsc_impressions', 'keyword__keyword')
        )
        if not rows:
            return {'success': True, 'keywords': 0, 'updated': 0}

        try:
            credentials = get_credentials_from_integration(integration)
            if not credentials:
                return {'success': False, 'error': 'No valid credentials found'}
            service = build('searchconsole', 'v1', credentials=credentials)
        except Exception as e:
            logger.error(f"[GSC Keywords] Could not build GSC client for integration {integration_id}: {e}")
            return {'success': False, 'error': str(e)}

        end_date = date.today() - timedelta(days=GSC_KEYWORD_LAG_DAYS)
        start_date = end_date - timedelta(days=GSC_KEYWORD_WINDOW_DAYS - 1)

        rows_by_country = defaultdict(list)
        for row in rows:
            rows_by_country[(row.isocode or '').lower()].append(row)

        changed, skipped, failed = [], [], []
        for isocode, country_rows in rows_by_country.items():
            country = GSC_COUNTRY_CODES.get(isocode)
            if not country:
                skipped.append(isocode)
                continue
            try:
                metrics = self._fetch_query_metrics(
                    service, integration.provider_id, start_date, end_date, country
                )
            except Exception as e:
                logger.error(
                    f"[GSC Keywords] Query fetch failed for integration {integration_id} "
                    f"country {country}: {e}"
                )
                failed.append(isocode)
                continue

            for row in country_rows:
                clicks, impressions = metrics.get(_normalise_query(row.keyword.keyword), (0, 0))
                if (row.gsc_clicks, row.gsc_impressions) != (clicks, impressions):
                    row.gsc_clicks, row.gsc_impressions = clicks, impressions
                    changed.append(row)

        SeoKeywordRank.objects.bulk_update(changed, ['gsc_clicks', 'gsc_impressions'], batch_size=500)

        if skipped:
            logger.warning(
                f"[GSC Keywords] integration {integration_id}: no GSC country code for {skipped}, skipped"
            )
        return {
            'success': not failed,
            'keywords': len(rows),
            'updated': len(changed),
            'window': f'{start_date}..{end_date}',
            'skipped_countries': skipped,
            'failed_countries': failed,
        }

    def _fetch_query_metrics(self, service, site_url: str, start_date: date, end_date: date,
                             country: str) -> Dict[str, tuple]:
        """
        Every query's (clicks, impressions) for one country, keyed by normalised
        text. Pages past the API's 25,000-row cap up to GSC_KEYWORD_SYNC_MAX_ROWS.
        Raises on API errors so the caller can leave that country untouched.
        """
        max_rows = getattr(settings, 'GSC_KEYWORD_SYNC_MAX_ROWS', 100000)
        metrics = {}
        start_row = 0
        while start_row < max_rows:
            response = service.searchanalytics().query(siteUrl=site_url, body={
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['query'],
                'dimensionFilterGroups': [{
                    'filters': [{'dimension': 'country', 'operator': 'equals', 'expression': country}],
                }],
                'rowLimit': GSC_MAX_PAGE_ROWS,
                'startRow': start_row,
            }).execute()

            page = response.get('rows', [])
            for r in page:
                key = _normalise_query((r.get('keys') or [''])[0])
                clicks, impressions = metrics.get(key, (0, 0))
                metrics[key] = (clicks + int(r.get('clicks', 0)), impressions + int(r.get('impressions', 0)))

            if len(page) < GSC_MAX_PAGE_ROWS:
                break
            start_row += GSC_MAX_PAGE_ROWS
        return metrics

    def _fetch_gsc_data(self, insight: GSCTrafficInsight, integration: Integration,
                       start_date: date, end_date: date) -> Dict[str, Any]:
        """Fetch data from Google Search Console API"""
        try:
            credentials = get_credentials_from_integration(integration)
            if not credentials:
                return {'success': False, 'error': 'No valid credentials found'}
            
            service = build('searchconsole', 'v1', credentials=credentials)
            site_url = integration.provider_id
            
            # Each section swallows its own error so one bad dimension does not
            # discard the rest, but the failures are collected: a section that
            # errored is NOT the same as a section with genuinely no traffic,
            # and reporting both as an empty COMP makes a broken sync
            # indistinguishable from an idle site.
            section_failures = []

            # Fetch overall metrics
            overall_data = self._fetch_overall_metrics(service, site_url, start_date, end_date,
                                                       failures=section_failures)

            # Fetch top queries
            top_rows = getattr(settings, 'GSC_TOP_ROWS_LIMIT', 100)
            top_queries = self._fetch_top_queries(service, site_url, start_date, end_date,
                                                  limit=top_rows, failures=section_failures)

            # Fetch top pages
            top_pages = self._fetch_top_pages(service, site_url, start_date, end_date,
                                              limit=top_rows, failures=section_failures)

            # Fetch device breakdown
            device_data = self._fetch_device_breakdown(service, site_url, start_date, end_date,
                                                       failures=section_failures)

            # Fetch country breakdown
            country_data = self._fetch_country_breakdown(service, site_url, start_date, end_date,
                                                         failures=section_failures)

            # Every section failed — there is no data at all, so this is a real
            # failure rather than a partial one and must not be stored as COMP.
            if len(section_failures) == TOTAL_GSC_SECTIONS:
                return {
                    'success': False,
                    'error': 'All GSC sections failed: ' + ', '.join(section_failures),
                }

            # Update insight with all data
            insight.total_impressions = overall_data.get('impressions', 0)
            insight.total_clicks = overall_data.get('clicks', 0)
            insight.avg_ctr = Decimal(str(overall_data.get('ctr', 0)))
            insight.avg_position = Decimal(str(overall_data.get('position', 0)))
            insight.top_queries = top_queries
            insight.top_pages = top_pages
            insight.device_breakdown = device_data
            insight.country_breakdown = country_data
            insight.save()

            return {'success': True, 'partial_failures': section_failures}
            
        except HttpError as e:
            logger.error(f"Google Search Console API error: {e}")
            return {'success': False, 'error': f'GSC API error: {str(e)}'}
        except Exception as e:
            logger.error(f"Error fetching GSC data: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _fetch_overall_metrics(self, service, site_url: str, start_date: date, end_date: date,
                               failures: list = None) -> Dict[str, Any]:
        """Fetch overall metrics from GSC. Records its name in `failures` if it errors."""
        try:
            request = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': [],
                'rowLimit': 1
            }
            
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            
            if not response.get('rows'):
                return {}
            
            row = response['rows'][0]
            
            impressions = row.get('impressions', 0)
            clicks = row.get('clicks', 0)
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            position = row.get('position', 0)
            
            return {
                'impressions': impressions,
                'clicks': clicks,
                'ctr': ctr,
                'position': position
            }
        except Exception as e:
            logger.error(f"Error fetching overall metrics: {e}")
            if failures is not None:
                failures.append('overall metrics')
            return {}
    
    def _fetch_top_queries(self, service, site_url: str, start_date: date, end_date: date, limit: int = 10,
                           failures: list = None) -> list:
        """Fetch top search queries. Records its name in `failures` if it errors."""
        queries = []
        
        try:
            request = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['query'],
                'rowLimit': limit,
                'orderBys': [{
                    'dimension': 'clicks',
                    'sortOrder': 'DESCENDING'
                }]
            }
            
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            
            for row in response.get('rows', []):
                keys = row.get('keys', [])
                query = keys[0] if keys else 'Unknown'
                impressions = row.get('impressions', 0)
                clicks = row.get('clicks', 0)
                ctr = (clicks / impressions * 100) if impressions > 0 else 0
                position = row.get('position', 0)
                
                queries.append({
                    'query': query,
                    'impressions': impressions,
                    'clicks': clicks,
                    'ctr': f"{ctr:.1f}%",
                    'position': round(position, 1)
                })
                
        except Exception as e:
            logger.error(f"Error fetching top queries: {e}")
            if failures is not None:
                failures.append('top queries')

        return queries
    
    def _fetch_top_pages(self, service, site_url: str, start_date: date, end_date: date, limit: int = 10,
                         failures: list = None) -> list:
        """Fetch top pages. Records its name in `failures` if it errors."""
        pages = []
        
        try:
            request = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['page'],
                'rowLimit': limit,
                'orderBys': [{
                    'dimension': 'clicks',
                    'sortOrder': 'DESCENDING'
                }]
            }
            
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            
            for row in response.get('rows', []):
                keys = row.get('keys', [])
                page = keys[0] if keys else 'Unknown'
                impressions = row.get('impressions', 0)
                clicks = row.get('clicks', 0)
                ctr = (clicks / impressions * 100) if impressions > 0 else 0
                position = row.get('position', 0)
                
                pages.append({
                    'page': page,
                    'impressions': impressions,
                    'clicks': clicks,
                    'ctr': f"{ctr:.1f}%",
                    'position': round(position, 1)
                })
                
        except Exception as e:
            logger.error(f"Error fetching top pages: {e}")
            if failures is not None:
                failures.append('top pages')

        return pages
    
    def _fetch_device_breakdown(self, service, site_url: str, start_date: date, end_date: date,
                                failures: list = None) -> Dict[str, Any]:
        """Fetch device breakdown. Records its name in `failures` if it errors."""
        device_data = {}
        
        try:
            request = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['device'],
                # GSC only ever returns DESKTOP / MOBILE / TABLET, so 10 can
                # never truncate this section — deliberately not configurable.
                'rowLimit': 10
            }
            
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            
            for row in response.get('rows', []):
                keys = row.get('keys', [])
                device = keys[0] if keys else 'Unknown'
                impressions = row.get('impressions', 0)
                clicks = row.get('clicks', 0)
                ctr = (clicks / impressions * 100) if impressions > 0 else 0
                
                device_data[device] = {
                    'impressions': impressions,
                    'clicks': clicks,
                    'ctr': f"{ctr:.1f}%"
                }
                
        except Exception as e:
            logger.error(f"Error fetching device breakdown: {e}")
            if failures is not None:
                failures.append('device breakdown')

        return device_data
    
    def _fetch_country_breakdown(self, service, site_url: str, start_date: date, end_date: date,
                                 failures: list = None) -> Dict[str, Any]:
        """Fetch country breakdown. Records its name in `failures` if it errors."""
        country_data = {}
        
        try:
            request = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['country'],
                'rowLimit': getattr(settings, 'GSC_COUNTRY_ROWS_LIMIT', 25),
                'orderBys': [{
                    'dimension': 'clicks',
                    'sortOrder': 'DESCENDING'
                }]
            }
            
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            
            for row in response.get('rows', []):
                keys = row.get('keys', [])
                country = keys[0] if keys else 'Unknown'
                impressions = row.get('impressions', 0)
                clicks = row.get('clicks', 0)
                ctr = (clicks / impressions * 100) if impressions > 0 else 0
                
                country_data[country] = {
                    'impressions': impressions,
                    'clicks': clicks,
                    'ctr': f"{ctr:.1f}%"
                }
                
        except Exception as e:
            logger.error(f"Error fetching country breakdown: {e}")
            if failures is not None:
                failures.append('country breakdown')

        return country_data

