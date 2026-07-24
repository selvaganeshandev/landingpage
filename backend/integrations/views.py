from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.utils import timezone
from .models import Integration, GATrafficInsight, GSCTrafficInsight
from .serializers import IntegrationSerializer, IntegrationPublicSerializer
from core.queryset_scoping import filter_by_accessible_domains
from .utils.prorate import apply_prorate_gsc, apply_prorate_ga


class IntegrationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Use public serializer for list/retrieve, full serializer for create/update."""
        if self.action in ['list', 'retrieve']:
            return IntegrationPublicSerializer
        return IntegrationSerializer
    
    def get_queryset(self):
        user = self.request.user
        # Scoped to the user's accessible domains — tenant + domain isolation.
        return filter_by_accessible_domains(Integration.objects.all(), user, self.request)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test the integration connection."""
        integration = self.get_object()
        
        # TODO: Implement actual connection testing logic based on integration type
        # For now, just mark as active
        integration.status = 'active'
        integration.last_sync_at = timezone.now()
        integration.error_message = None
        integration.save()
        
        return Response({
            'status': 'success',
            'message': f'{integration.get_type_display()} connection is active'
        })
    
    @action(detail=True, methods=['post'])
    def disconnect(self, request, pk=None):
        """Disconnect the integration."""
        integration = self.get_object()
        integration.status = 'disconnected'
        integration.credentials = {}  # Clear credentials
        integration.save()
        
        return Response({
            'status': 'disconnected',
            'message': f'{integration.get_type_display()} has been disconnected'
        })
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Manually trigger a sync for this integration."""
        integration = self.get_object()
        
        # TODO: Implement actual sync logic based on integration type
        # For now, just update the last_sync_at timestamp
        integration.last_sync_at = timezone.now()
        integration.save()
        
        return Response({
            'status': 'synced',
            'last_sync_at': integration.last_sync_at
        })
    
    @action(detail=False, methods=['get'])
    def by_domain(self, request):
        """Get all integrations for a specific domain."""
        domain_id = request.query_params.get('domain_id')
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(domain_id=domain_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_secondary(self, request):
        """Get all integrations for a report-only secondary subdomain.

        Secondary integrations have domain IS NULL, so they're scoped by the
        subdomain's organisation rather than by domain (the default queryset).
        """
        secondary_id = request.query_params.get('secondary_id')
        if not secondary_id:
            return Response(
                {'error': 'secondary_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        # Org-scoped for all roles (including super_admin) — tenant isolation.
        queryset = Integration.objects.filter(
            secondary_domain_id=secondary_id,
            secondary_domain__organisation=user.organisation,
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def status_summary(self, request):
        """Get integration status summary."""
        domain_id = request.query_params.get('domain_id')
        queryset = self.get_queryset()
        
        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)
        
        summary = {
            'total': queryset.count(),
            'active': queryset.filter(status='active').count(),
            'error': queryset.filter(status='error').count(),
            'disconnected': queryset.filter(status='disconnected').count(),
        }
        return Response(summary)
    
    @action(detail=True, methods=['post'])
    def start_processing(self, request, pk=None):
        """Start processing insights for this integration."""
        integration = self.get_object()
        
        if not integration.provider_id or integration.provider_id == '':
            return Response(
                {'error': 'No property/site selected for this integration'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Import tasks from engine
        import sys
        import os
        import importlib.util
        
        # Add engine to path and ensure it's prioritized
        engine_path = os.path.join(os.path.dirname(__file__), '../../engine')
        engine_path = os.path.abspath(engine_path)
        
        # Remove engine path if already there, then add to front
        if engine_path in sys.path:
            sys.path.remove(engine_path)
        sys.path.insert(0, engine_path)
        
        # Temporarily remove ALL integrations modules (including the package itself) to avoid conflicts
        # This ensures Python will find the engine's integrations package
        integrations_modules = [k for k in list(sys.modules.keys()) if k.startswith('integrations')]
        temp_removed = {}
        for mod_name in integrations_modules:
            temp_removed[mod_name] = sys.modules.pop(mod_name, None)
        
        try:
            from core.processing_tasks import process_ga_insights_task, process_gsc_insights_task
        finally:
            # Restore backend's integrations modules
            for mod_name, mod_obj in temp_removed.items():
                if mod_obj is not None:
                    sys.modules[mod_name] = mod_obj
        
        days_back = request.data.get('days_back', 30)
        
        if integration.type == 'google_analytics':
            task = process_ga_insights_task.delay(integration.id, days_back)
        elif integration.type == 'search_console':
            task = process_gsc_insights_task.delay(integration.id, days_back)
        else:
            return Response(
                {'error': 'Integration type not supported for processing'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'success': True,
            'task_id': task.id,
            'message': f'Processing started for {integration.get_type_display()}'
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_traffic_processing(request):
    """
    DEPRECATED: This endpoint is kept for backward compatibility.
    Please use the engine endpoints instead:
    - POST /api/integrations/scheduler/start/ (in engine)
    - POST /api/integrations/process-pending/ (in engine)
    """
    return Response({
        'error': 'This endpoint is deprecated. Please use engine endpoints at /api/integrations/scheduler/start/ or /api/integrations/process-pending/',
        'engine_endpoints': {
            'scheduler': '/api/integrations/scheduler/start/',
            'process_pending': '/api/integrations/process-pending/',
            'get_pending': '/api/integrations/pending-insights/'
        }
    }, status=status.HTTP_410_GONE)


def _extract_main_keyword(article_title):
    """Use Gemini to extract the main search keyword from an article title."""
    from domains.views import get_google_genai_client

    genai = get_google_genai_client()
    model = genai.GenerativeModel(settings.GEMINI_MODEL)

    prompt = (
        f'Extract the single most important search keyword or short phrase '
        f'(2-4 words) from this article title. Return ONLY the keyword, nothing else.\n\n'
        f'Article title: "{article_title}"'
    )

    response = model.generate_content(prompt)
    return response.text.strip().strip('"').strip("'").lower()


def _fetch_gsc_keywords_by_query(integration, keyword):
    """Fetch related keywords from GSC Search Analytics API filtered by keyword."""
    from .google_oauth import get_credentials_from_integration
    from googleapiclient.discovery import build
    from datetime import date, timedelta

    credentials = get_credentials_from_integration(integration)
    if not credentials:
        return []

    service = build('searchconsole', 'v1', credentials=credentials)
    site_url = integration.provider_id

    end_date = date.today() - timedelta(days=3)  # GSC data has ~3 day lag
    start_date = end_date - timedelta(days=30)

    request_body = {
        'startDate': start_date.isoformat(),
        'endDate': end_date.isoformat(),
        'dimensions': ['query'],
        'dimensionFilterGroups': [{
            'filters': [{
                'dimension': 'query',
                'operator': 'contains',
                'expression': keyword
            }]
        }],
        'rowLimit': 50,
    }

    response = service.searchanalytics().query(
        siteUrl=site_url, body=request_body
    ).execute()

    keywords = []
    for row in response.get('rows', []):
        keys = row.get('keys', [])
        if keys:
            keywords.append({
                'keyword': keys[0],
                'clicks': row.get('clicks', 0),
                'impressions': row.get('impressions', 0),
                'ctr': round(row.get('ctr', 0) * 100, 2),
                'position': round(row.get('position', 0), 1),
            })

    return keywords


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_gsc_keywords(request):
    """
    Get GSC keywords (top queries) for a domain.
    GET /api/integrations/gsc-keywords/?domain_id=1
    GET /api/integrations/gsc-keywords/?domain_id=1&article_title=Best+Protein+Powders
    """
    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Check if GSC integration exists and is active
        gsc_integration = Integration.objects.filter(
            domain_id=domain_id,
            type='search_console',
            status='active'
        ).first()

        if not gsc_integration:
            return Response({
                'connected': False,
                'message': 'Google Search Console is not connected for this domain'
            })

        # Check if a GSC property/site has been selected
        if not gsc_integration.provider_id or gsc_integration.provider_id in ('', 'pending_selection'):
            return Response({
                'connected': False,
                'message': 'Google Search Console is connected but no site has been selected. Please select a site in Domain Settings → Integrations.'
            })

        # If article_title provided, use Gemini + live GSC API for keyword-filtered results
        article_title = request.query_params.get('article_title', '').strip()
        if article_title:
            try:
                main_keyword = _extract_main_keyword(article_title)
                keywords = _fetch_gsc_keywords_by_query(gsc_integration, main_keyword)
                return Response({
                    'connected': True,
                    'keywords': keywords,
                    'main_keyword': main_keyword,
                    'total_keywords': len(keywords)
                })
            except Exception:
                pass  # Fall through to cached data below

        # Get latest GSC insight with top queries
        gsc_insight = GSCTrafficInsight.objects.filter(
            domain_id=domain_id,
            track_status='COMP'
        ).order_by('-end_date', '-created_at').first()

        if not gsc_insight or not gsc_insight.top_queries:
            return Response({
                'connected': True,
                'keywords': [],
                'message': 'No GSC data available yet. Please sync your GSC integration first.'
            })

        # Extract keywords from top_queries with full data
        # top_queries is a list of dicts like [{"query": "keyword", "clicks": 100, "impressions": 500, ...}, ...]
        keywords = []
        for query_data in gsc_insight.top_queries:
            if isinstance(query_data, dict) and 'query' in query_data:
                keywords.append({
                    'keyword': query_data['query'],
                    'clicks': query_data.get('clicks', 0),
                    'impressions': query_data.get('impressions', 0),
                    'ctr': query_data.get('ctr', 0),
                    'position': query_data.get('position', 0),
                })
            elif isinstance(query_data, str):
                keywords.append({
                    'keyword': query_data,
                    'clicks': 0,
                    'impressions': 0,
                    'ctr': 0,
                    'position': 0,
                })

        return Response({
            'connected': True,
            'keywords': keywords[:100],  # Limit to top 100 keywords
            'total_keywords': len(keywords)
        })

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_traffic_insights(request):
    """
    Get traffic insights for a domain.
    GET /api/integrations/traffic-insights/?domain_id=1
    """
    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Get latest GA insight
        ga_insight = GATrafficInsight.objects.filter(
            domain_id=domain_id,
            track_status='COMP'
        ).order_by('-end_date', '-created_at').first()
        
        # Get latest GSC insight
        gsc_insight = GSCTrafficInsight.objects.filter(
            domain_id=domain_id,
            track_status='COMP'
        ).order_by('-end_date', '-created_at').first()
        
        # Format response
        response_data = {
            'ga': None,
            'gsc': None
        }
        
        if ga_insight:
            raw_ga = {
                'id': ga_insight.id,
                'start_date': ga_insight.start_date.isoformat(),
                'end_date': ga_insight.end_date.isoformat(),
                'total_sessions': ga_insight.total_sessions,
                'total_users': ga_insight.total_users,
                'total_page_views': ga_insight.total_page_views,
                'total_conversions': ga_insight.total_conversions,
                'total_revenue': float(ga_insight.total_revenue),
                'bounce_rate': float(ga_insight.bounce_rate),
                'avg_session_duration': float(ga_insight.avg_session_duration),
                'platform_breakdown': ga_insight.platform_breakdown,
                'device_breakdown': ga_insight.device_breakdown,
                'geographic_breakdown': ga_insight.geographic_breakdown,
                'landing_pages': ga_insight.landing_pages,
                'conversion_paths': ga_insight.conversion_paths,
                'updated_at': ga_insight.updated_at.isoformat(),
            }
            response_data['ga'] = apply_prorate_ga(raw_ga, ga_insight.start_date, ga_insight.end_date)

        if gsc_insight:
            raw_gsc = {
                'id': gsc_insight.id,
                'start_date': gsc_insight.start_date.isoformat(),
                'end_date': gsc_insight.end_date.isoformat(),
                'total_impressions': gsc_insight.total_impressions,
                'total_clicks': gsc_insight.total_clicks,
                'avg_ctr': float(gsc_insight.avg_ctr),
                'avg_position': float(gsc_insight.avg_position),
                'top_queries': gsc_insight.top_queries,
                'top_pages': gsc_insight.top_pages,
                'device_breakdown': gsc_insight.device_breakdown,
                'country_breakdown': gsc_insight.country_breakdown,
                'updated_at': gsc_insight.updated_at.isoformat(),
            }
            response_data['gsc'] = apply_prorate_gsc(raw_gsc, gsc_insight.start_date, gsc_insight.end_date)
        
        return Response(response_data)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

