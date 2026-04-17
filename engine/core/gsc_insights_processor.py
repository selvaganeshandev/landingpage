"""
GSC Insights Processor: Fetches and stores Google Search Console traffic data
"""
import logging
from typing import Dict, Any
from datetime import datetime, timedelta, date
import calendar
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

# Import from engine's integrations app
from integrations.models import Integration, GSCTrafficInsight
from shared_models.models import Domain
from integrations.google_oauth_helper import get_credentials_from_integration
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


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
                    insight.track_message = 'Successfully processed'
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
                    insight.track_message = 'Successfully processed'
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

    def _fetch_gsc_data(self, insight: GSCTrafficInsight, integration: Integration,
                       start_date: date, end_date: date) -> Dict[str, Any]:
        """Fetch data from Google Search Console API"""
        try:
            credentials = get_credentials_from_integration(integration)
            if not credentials:
                return {'success': False, 'error': 'No valid credentials found'}
            
            service = build('searchconsole', 'v1', credentials=credentials)
            site_url = integration.provider_id
            
            # Fetch overall metrics
            overall_data = self._fetch_overall_metrics(service, site_url, start_date, end_date)
            
            # Fetch top queries
            top_queries = self._fetch_top_queries(service, site_url, start_date, end_date)
            
            # Fetch top pages
            top_pages = self._fetch_top_pages(service, site_url, start_date, end_date)
            
            # Fetch device breakdown
            device_data = self._fetch_device_breakdown(service, site_url, start_date, end_date)
            
            # Fetch country breakdown
            country_data = self._fetch_country_breakdown(service, site_url, start_date, end_date)
            
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
            
            return {'success': True}
            
        except HttpError as e:
            logger.error(f"Google Search Console API error: {e}")
            return {'success': False, 'error': f'GSC API error: {str(e)}'}
        except Exception as e:
            logger.error(f"Error fetching GSC data: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _fetch_overall_metrics(self, service, site_url: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """Fetch overall metrics from GSC"""
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
            return {}
    
    def _fetch_top_queries(self, service, site_url: str, start_date: date, end_date: date, limit: int = 10) -> list:
        """Fetch top search queries"""
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
        
        return queries
    
    def _fetch_top_pages(self, service, site_url: str, start_date: date, end_date: date, limit: int = 10) -> list:
        """Fetch top pages"""
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
        
        return pages
    
    def _fetch_device_breakdown(self, service, site_url: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """Fetch device breakdown"""
        device_data = {}
        
        try:
            request = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['device'],
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
        
        return device_data
    
    def _fetch_country_breakdown(self, service, site_url: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """Fetch country breakdown"""
        country_data = {}
        
        try:
            request = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['country'],
                'rowLimit': 10,
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
        
        return country_data

