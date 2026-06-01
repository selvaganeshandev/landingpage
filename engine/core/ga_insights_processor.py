"""
GA Insights Processor: Fetches and stores Google Analytics traffic data
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, date
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

# Import from engine's integrations app
from integrations.models import Integration, GATrafficInsight
from shared_models.models import Domain
from integrations.google_oauth_helper import get_credentials_from_integration
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# AI platform domains to track
AI_PLATFORMS = {
    'chat.openai.com': 'ChatGPT',
    'chatgpt.com': 'ChatGPT',
    'claude.ai': 'Claude',
    'gemini.google.com': 'Gemini',
    'bard.google.com': 'Gemini',
    'perplexity.ai': 'Perplexity',
    'grok.x.ai': 'Grok',
    'grok.com': 'Grok',
    'chat.deepseek.com': 'DeepSeek',
    'deepseek.com': 'DeepSeek',
    'you.com': 'You.com',
    'poe.com': 'Poe',
}


class GAInsightsProcessor:
    """
    Processor for fetching and storing Google Analytics traffic insights
    """
    
    def process_insight(self, insight_id: int) -> Dict[str, Any]:
        """
        Process a specific GA insight record
        
        Args:
            insight_id: ID of the GATrafficInsight record to process
            
        Returns:
            Dict with processing results
        """
        try:
            with transaction.atomic():
                insight = GATrafficInsight.objects.select_for_update().get(id=insight_id)
                
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
                    insight.track_message = 'No property selected for this integration'
                    insight.save()
                    return {
                        'success': False,
                        'error': 'No property selected for this integration'
                    }
                
                # Check if same integration is already processing
                if GATrafficInsight.objects.filter(
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
                insight.track_message = 'Fetching data from Google Analytics'
                insight.save()
            
            # Fetch data from GA
            result = self._fetch_ga_data(insight, integration, insight.start_date, insight.end_date)
            
            if result['success']:
                with transaction.atomic():
                    insight = GATrafficInsight.objects.select_for_update().get(id=insight.id)
                    insight.track_status = 'COMP'
                    insight.track_message = 'Successfully processed'
                    insight.save()
                
                logger.info(f"Successfully processed GA insight {insight_id}")
                return {
                    'success': True,
                    'insight_id': insight.id,
                    'message': 'GA insights processed successfully'
                }
            else:
                with transaction.atomic():
                    insight = GATrafficInsight.objects.select_for_update().get(id=insight.id)
                    insight.track_status = 'FAIL'
                    insight.track_message = result.get('error', 'Unknown error')
                    insight.save()
                
                return result
                
        except GATrafficInsight.DoesNotExist:
            logger.error(f"GA insight {insight_id} not found")
            return {
                'success': False,
                'error': 'Insight not found'
            }
        except Exception as e:
            logger.error(f"Error processing GA insight {insight_id}: {str(e)}", exc_info=True)
            # Try to mark as failed
            try:
                with transaction.atomic():
                    insight = GATrafficInsight.objects.select_for_update().get(id=insight_id)
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
        Process GA insights for a specific integration
        
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
                    type='google_analytics',
                    status='active'
                )
                
                if not integration.provider_id or integration.provider_id == '':
                    logger.warning(f"Integration {integration_id} has no provider_id set")
                    return {
                        'success': False,
                        'error': 'No property selected for this integration'
                    }
                
                # Check if already processing
                if integration.ga_insights.filter(track_status='PROC').exists():
                    logger.info(f"Integration {integration_id} already has processing insight")
                    return {
                        'success': False,
                        'error': 'Already processing'
                    }
                
                # Calculate date range
                end_date = date.today()
                start_date = end_date - timedelta(days=days_back)
                
                # Create or get insight record
                insight, created = GATrafficInsight.objects.get_or_create(
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
                insight.track_message = 'Fetching data from Google Analytics'
                insight.save()
            
            # Fetch data from GA
            result = self._fetch_ga_data(insight, integration, start_date, end_date)
            
            if result['success']:
                with transaction.atomic():
                    insight = GATrafficInsight.objects.select_for_update().get(id=insight.id)
                    insight.track_status = 'COMP'
                    insight.track_message = 'Successfully processed'
                    insight.save()
                
                logger.info(f"Successfully processed GA insights for integration {integration_id}")
                return {
                    'success': True,
                    'insight_id': insight.id,
                    'message': 'GA insights processed successfully'
                }
            else:
                with transaction.atomic():
                    insight = GATrafficInsight.objects.select_for_update().get(id=insight.id)
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
            logger.error(f"Error processing GA insights for integration {integration_id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_monthly_insights(self, integration_id: int) -> Dict[str, Any]:
        """
        Create/update 3 calendar-month-aligned GA insight records for MoM and YoY.

        Records created:
          current_month  — first day → last day of this month  (incomplete, prorated in API)
          prev_month     — first → last day of previous month  (complete)
          yoy_month      — same month last year                (complete)

        Uses get_or_create on (integration, start_date, end_date) so the same
        record is refreshed each day without creating duplicates.
        The existing scheduler picks up INIT records and processes them normally.
        """
        import calendar as _calendar
        try:
            integration = Integration.objects.get(
                id=integration_id, type='google_analytics', status='active'
            )

            if not integration.provider_id or integration.provider_id == '':
                return {'success': False, 'error': 'No property selected for this integration'}

            today = date.today()
            month_start = today.replace(day=1)
            month_last_day = _calendar.monthrange(today.year, today.month)[1]
            month_end = today.replace(day=month_last_day)

            # Previous month
            if today.month == 1:
                prev_year, prev_month = today.year - 1, 12
            else:
                prev_year, prev_month = today.year, today.month - 1
            prev_start = date(prev_year, prev_month, 1)
            prev_last_day = _calendar.monthrange(prev_year, prev_month)[1]
            prev_end = date(prev_year, prev_month, prev_last_day)

            # Same month last year
            yoy_year = today.year - 1
            yoy_last_day = _calendar.monthrange(yoy_year, today.month)[1]
            yoy_start = date(yoy_year, today.month, 1)
            yoy_end = date(yoy_year, today.month, yoy_last_day)

            periods = [
                ('current_month', month_start, month_end),
                ('prev_month',    prev_start,  prev_end),
                ('yoy_month',     yoy_start,   yoy_end),
            ]

            created_ids = []
            for period_type, start, end in periods:
                insight, created = GATrafficInsight.objects.get_or_create(
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
                    GATrafficInsight.objects.filter(id=insight.id).update(
                        period_type=period_type,
                        track_status='INIT',
                        track_message=None,
                    )
                    logger.info(
                        f"GA monthly insight reset to INIT: integration={integration_id} "
                        f"period={period_type} ({start}→{end})"
                    )
                else:
                    logger.info(
                        f"GA monthly insight created: integration={integration_id} "
                        f"period={period_type} ({start}→{end})"
                    )
                created_ids.append(insight.id)

            return {
                'success': True,
                'insight_ids': created_ids,
                'message': f'Scheduled {len(created_ids)} monthly GA insight records'
            }

        except Integration.DoesNotExist:
            return {'success': False, 'error': f'Integration {integration_id} not found or not active'}
        except Exception as e:
            logger.error(f"Error scheduling monthly GA insights for integration {integration_id}: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _fetch_ga_data(self, insight: GATrafficInsight, integration: Integration,
                      start_date: date, end_date: date) -> Dict[str, Any]:
        """Fetch data from Google Analytics API"""
        try:
            credentials = get_credentials_from_integration(integration)
            if not credentials:
                return {'success': False, 'error': 'No valid credentials found'}
            
            service = build('analyticsdata', 'v1beta', credentials=credentials)
            
            # Extract property ID
            property_id = integration.provider_id
            if not property_id.startswith('properties/'):
                property_id = f'properties/{property_id}'
            
            # Fetch overall metrics
            overall_data = self._fetch_overall_metrics(service, property_id, start_date, end_date)
            
            # Fetch AI platform breakdown
            platform_data = self._fetch_platform_breakdown(service, property_id, start_date, end_date)
            
            # Fetch device breakdown
            device_data = self._fetch_device_breakdown(service, property_id, start_date, end_date)
            
            # Fetch geographic breakdown
            geo_data = self._fetch_geographic_breakdown(service, property_id, start_date, end_date)
            
            # Fetch landing pages
            landing_pages = self._fetch_landing_pages(service, property_id, start_date, end_date)
            
            # Fetch conversion paths (if available)
            conversion_paths = self._fetch_conversion_paths(service, property_id, start_date, end_date)
            
            # Update insight with all data
            insight.total_sessions = overall_data.get('sessions', 0)
            insight.total_users = overall_data.get('users', 0)
            insight.total_page_views = overall_data.get('pageViews', 0)
            insight.total_conversions = overall_data.get('conversions', 0)
            insight.total_revenue = Decimal(str(overall_data.get('revenue', 0)))
            insight.bounce_rate = Decimal(str(overall_data.get('bounceRate', 0)))
            insight.avg_session_duration = Decimal(str(overall_data.get('avgSessionDuration', 0)))
            insight.platform_breakdown = platform_data
            insight.device_breakdown = device_data
            insight.geographic_breakdown = geo_data
            insight.landing_pages = landing_pages
            insight.conversion_paths = conversion_paths
            insight.save()
            
            return {'success': True}
            
        except HttpError as e:
            logger.error(f"Google Analytics API error: {e}")
            return {'success': False, 'error': f'GA API error: {str(e)}'}
        except Exception as e:
            logger.error(f"Error fetching GA data: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _fetch_overall_metrics(self, service, property_id: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """Fetch overall metrics from GA"""
        try:
            response = service.properties().runReport(
                property=property_id,
                body={
                    'dateRanges': [{
                        'startDate': start_date.strftime('%Y-%m-%d'),
                        'endDate': end_date.strftime('%Y-%m-%d')
                    }],
                    'metrics': [
                        {'name': 'sessions'},
                        {'name': 'totalUsers'},
                        {'name': 'screenPageViews'},
                        {'name': 'conversions'},
                        {'name': 'totalRevenue'},
                        {'name': 'bounceRate'},
                        {'name': 'averageSessionDuration'},
                    ],
                }
            ).execute()
            
            if not response.get('rows'):
                return {}
            
            row = response['rows'][0]
            metric_values = row.get('metricValues', [])
            
            return {
                'sessions': int(metric_values[0].get('value', 0)) if len(metric_values) > 0 else 0,
                'users': int(metric_values[1].get('value', 0)) if len(metric_values) > 1 else 0,
                'pageViews': int(metric_values[2].get('value', 0)) if len(metric_values) > 2 else 0,
                'conversions': int(metric_values[3].get('value', 0)) if len(metric_values) > 3 else 0,
                'revenue': float(metric_values[4].get('value', 0)) if len(metric_values) > 4 else 0,
                'bounceRate': float(metric_values[5].get('value', 0)) if len(metric_values) > 5 else 0,
                'avgSessionDuration': float(metric_values[6].get('value', 0)) if len(metric_values) > 6 else 0,
            }
        except Exception as e:
            logger.error(f"Error fetching overall metrics: {e}")
            return {}
    
    def _fetch_platform_breakdown(self, service, property_id: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """Fetch AI platform breakdown"""
        platform_data = {}
        
        try:
            # Filter for AI platform sources
            ai_sources = list(AI_PLATFORMS.keys())
            
            response = service.properties().runReport(
                property=property_id,
                body={
                    'dateRanges': [{
                        'startDate': start_date.strftime('%Y-%m-%d'),
                        'endDate': end_date.strftime('%Y-%m-%d')
                    }],
                    'dimensions': [{'name': 'sessionSource'}],
                    'metrics': [
                        {'name': 'sessions'},
                        {'name': 'conversions'},
                        {'name': 'totalRevenue'},
                        {'name': 'bounceRate'},
                        {'name': 'averageSessionDuration'},
                        {'name': 'totalUsers'},
                        {'name': 'screenPageViews'},
                    ],
                    'dimensionFilter': {
                        'filter': {
                            'fieldName': 'sessionSource',
                            'inListFilter': {
                                'values': ai_sources
                            }
                        }
                    },
                    'orderBys': [{
                        'metric': {'metricName': 'sessions'},
                        'desc': True
                    }]
                }
            ).execute()
            
            for row in response.get('rows', []):
                source = row.get('dimensionValues', [{}])[0].get('value', '')
                platform_name = AI_PLATFORMS.get(source, 'Other AI')
                metric_values = row.get('metricValues', [])
                
                if platform_name not in platform_data:
                    platform_data[platform_name] = {
                        'visits': 0,
                        'conversions': 0,
                        'revenue': 0,
                        'bounceRate': 0,
                        'avgDuration': 0,
                        'users': 0,
                        'pageViews': 0
                    }

                platform_data[platform_name]['visits'] += int(metric_values[0].get('value', 0)) if len(metric_values) > 0 else 0
                platform_data[platform_name]['conversions'] += int(metric_values[1].get('value', 0)) if len(metric_values) > 1 else 0
                platform_data[platform_name]['revenue'] += float(metric_values[2].get('value', 0)) if len(metric_values) > 2 else 0
                platform_data[platform_name]['bounceRate'] = float(metric_values[3].get('value', 0)) if len(metric_values) > 3 else 0
                platform_data[platform_name]['avgDuration'] = float(metric_values[4].get('value', 0)) if len(metric_values) > 4 else 0
                platform_data[platform_name]['users'] += int(metric_values[5].get('value', 0)) if len(metric_values) > 5 else 0
                platform_data[platform_name]['pageViews'] += int(metric_values[6].get('value', 0)) if len(metric_values) > 6 else 0
                
        except Exception as e:
            logger.error(f"Error fetching platform breakdown: {e}")
        
        return platform_data
    
    def _fetch_device_breakdown(self, service, property_id: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """Fetch device breakdown"""
        device_data = {}
        
        try:
            response = service.properties().runReport(
                property=property_id,
                body={
                    'dateRanges': [{
                        'startDate': start_date.strftime('%Y-%m-%d'),
                        'endDate': end_date.strftime('%Y-%m-%d')
                    }],
                    'dimensions': [{'name': 'deviceCategory'}],
                    'metrics': [
                        {'name': 'sessions'},
                        {'name': 'conversions'},
                        {'name': 'totalRevenue'},
                    ],
                }
            ).execute()
            
            total_sessions = 0
            for row in response.get('rows', []):
                device = row.get('dimensionValues', [{}])[0].get('value', 'Unknown')
                metric_values = row.get('metricValues', [])
                sessions = int(metric_values[0].get('value', 0)) if len(metric_values) > 0 else 0
                total_sessions += sessions
                
                device_data[device] = {
                    'sessions': sessions,
                    'conversions': int(metric_values[1].get('value', 0)) if len(metric_values) > 1 else 0,
                    'revenue': float(metric_values[2].get('value', 0)) if len(metric_values) > 2 else 0,
                }
            
            # Calculate percentages
            for device in device_data:
                if total_sessions > 0:
                    device_data[device]['percentage'] = round((device_data[device]['sessions'] / total_sessions) * 100, 1)
                else:
                    device_data[device]['percentage'] = 0
                    
        except Exception as e:
            logger.error(f"Error fetching device breakdown: {e}")
        
        return device_data
    
    def _fetch_geographic_breakdown(self, service, property_id: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """Fetch geographic breakdown"""
        geo_data = {}
        
        try:
            response = service.properties().runReport(
                property=property_id,
                body={
                    'dateRanges': [{
                        'startDate': start_date.strftime('%Y-%m-%d'),
                        'endDate': end_date.strftime('%Y-%m-%d')
                    }],
                    'dimensions': [{'name': 'country'}],
                    'metrics': [
                        {'name': 'sessions'},
                        {'name': 'totalRevenue'},
                    ],
                    'orderBys': [{
                        'metric': {'metricName': 'sessions'},
                        'desc': True
                    }],
                    'limit': 10
                }
            ).execute()
            
            total_sessions = 0
            for row in response.get('rows', []):
                country = row.get('dimensionValues', [{}])[0].get('value', 'Unknown')
                metric_values = row.get('metricValues', [])
                sessions = int(metric_values[0].get('value', 0)) if len(metric_values) > 0 else 0
                total_sessions += sessions
                
                geo_data[country] = {
                    'sessions': sessions,
                    'revenue': float(metric_values[1].get('value', 0)) if len(metric_values) > 1 else 0,
                }
            
            # Calculate percentages
            for country in geo_data:
                if total_sessions > 0:
                    geo_data[country]['percentage'] = round((geo_data[country]['sessions'] / total_sessions) * 100, 1)
                else:
                    geo_data[country]['percentage'] = 0
                    
        except Exception as e:
            logger.error(f"Error fetching geographic breakdown: {e}")
        
        return geo_data
    
    def _fetch_landing_pages(self, service, property_id: str, start_date: date, end_date: date) -> list:
        """Fetch top landing pages"""
        landing_pages = []
        
        try:
            response = service.properties().runReport(
                property=property_id,
                body={
                    'dateRanges': [{
                        'startDate': start_date.strftime('%Y-%m-%d'),
                        'endDate': end_date.strftime('%Y-%m-%d')
                    }],
                    'dimensions': [{'name': 'landingPage'}],
                    'metrics': [
                        {'name': 'sessions'},
                        {'name': 'bounceRate'},
                        {'name': 'averageSessionDuration'},
                        {'name': 'conversions'},
                    ],
                    'orderBys': [{
                        'metric': {'metricName': 'sessions'},
                        'desc': True
                    }],
                    'limit': 10
                }
            ).execute()
            
            for row in response.get('rows', []):
                page = row.get('dimensionValues', [{}])[0].get('value', '')
                metric_values = row.get('metricValues', [])
                
                landing_pages.append({
                    'page': page,
                    'sessions': int(metric_values[0].get('value', 0)) if len(metric_values) > 0 else 0,
                    'bounceRate': f"{float(metric_values[1].get('value', 0)):.1f}%" if len(metric_values) > 1 else "0%",
                    'avgDuration': self._format_duration(float(metric_values[2].get('value', 0))) if len(metric_values) > 2 else "0:00",
                    'conversions': int(metric_values[3].get('value', 0)) if len(metric_values) > 3 else 0,
                })
                
        except Exception as e:
            logger.error(f"Error fetching landing pages: {e}")
        
        return landing_pages
    
    def _fetch_conversion_paths(self, service, property_id: str, start_date: date, end_date: date) -> list:
        """Fetch conversion paths (simplified - would need more complex query)"""
        # This is a simplified version - full conversion path analysis would require more complex queries
        return []
    
    def _format_duration(self, seconds: float) -> str:
        """Format seconds to MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

