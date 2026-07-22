"""
API Views for Misinformation Module
"""
import logging
from datetime import date, timedelta
from urllib.parse import urlparse
from collections import Counter
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from domains.models import Domain
from prompts.models import PromptAnalytics
from .models import (
    MisinformationScan,
    MisinformationAlert,
    MisinformationAnalytics,
    CitationURL,
    CitationContent,
    CitationMention,
)
from .serializers import (
    MisinformationAlertListSerializer,
    MisinformationAlertDetailSerializer,
    MisinformationAlertUpdateSerializer,
    MisinformationScanSerializer,
    MisinformationAnalyticsSerializer,
    DashboardSerializer,
    TriggerScanSerializer,
    CitationURLSerializer,
)
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """
    Get misinformation dashboard summary.

    Query params:
        domain_id: Required - ID of the domain
        days: Optional - Number of days for trend (default: 30)
    """
    domain_id = request.query_params.get('domain_id')
    days = int(request.query_params.get('days', 30))

    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        domain = Domain.objects.get(id=domain_id)
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Get all alerts for domain
    all_alerts = MisinformationAlert.objects.filter(domain=domain)

    # Active alerts (new, reviewed = still open)
    active_statuses = ['new', 'reviewed']
    active_alerts = all_alerts.filter(status__in=active_statuses)

    # Resolved alerts
    resolved_statuses = ['resolved', 'dismissed']
    resolved_alerts = all_alerts.filter(status__in=resolved_statuses)

    # Calculate totals
    total_detected = all_alerts.count()
    active_cases = active_alerts.count()
    resolved_cases = resolved_alerts.count()
    broken_links = all_alerts.filter(alert_type='broken_link').count()
    misinformation = all_alerts.filter(alert_type='misinformation').count()
    outdated = all_alerts.filter(alert_type='outdated').count()

    by_severity = {
        'low': active_alerts.filter(severity='low').count(),
        'medium': active_alerts.filter(severity='medium').count(),
        'high': active_alerts.filter(severity='high').count(),
        'critical': active_alerts.filter(severity='critical').count(),
    }

    # Calculate average response time (from created to reviewed)
    resolved_with_times = resolved_alerts.exclude(reviewed_at__isnull=True)
    avg_response_time_hours = 0
    if resolved_with_times.exists():
        total_hours = 0
        count = 0
        for alert in resolved_with_times:
            if alert.reviewed_at and alert.created_at:
                diff = alert.reviewed_at - alert.created_at
                total_hours += diff.total_seconds() / 3600
                count += 1
        if count > 0:
            avg_response_time_hours = total_hours / count

    # Get recent alerts
    recent_alerts = all_alerts.order_by('-created_at')[:10]

    # Get trend data for comparison
    start_date = date.today() - timedelta(days=days)
    previous_start = start_date - timedelta(days=days)

    # Current period counts
    current_total = all_alerts.filter(created_at__date__gte=start_date).count()
    current_resolved = resolved_alerts.filter(reviewed_at__date__gte=start_date).count()

    # Previous period counts
    previous_total = all_alerts.filter(
        created_at__date__gte=previous_start,
        created_at__date__lt=start_date
    ).count()
    previous_resolved = resolved_alerts.filter(
        reviewed_at__date__gte=previous_start,
        reviewed_at__date__lt=start_date
    ).count()

    # Calculate percentage changes
    def calc_change(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100)

    trends = {
        'total_detected_change': calc_change(current_total, previous_total),
        'active_cases_change': 0,  # Would need historical data for this
        'response_time_change': 0,  # Would need historical data for this
        'resolved_change': calc_change(current_resolved, previous_resolved),
    }

    # Get analytics trend data
    trend = MisinformationAnalytics.objects.filter(
        domain=domain,
        date__gte=start_date
    ).order_by('date')

    data = {
        'total_detected': total_detected,
        'active_cases': active_cases,
        'resolved_cases': resolved_cases,
        'broken_links': broken_links,
        'misinformation': misinformation,
        'outdated_content': outdated,
        'by_severity': by_severity,
        'avg_response_time_hours': round(avg_response_time_hours, 1),
        'trends': trends,
        'recent_alerts': MisinformationAlertListSerializer(recent_alerts, many=True).data,
        'trend_data': MisinformationAnalyticsSerializer(trend, many=True).data,
        # Domain scan status info
        'scan_status': domain.misinformation_scan_status,
        'last_scan_at': domain.last_misinformation_scan_at,
    }

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def alert_list(request):
    """
    List misinformation alerts with filtering.

    Query params:
        domain_id: Required - ID of the domain
        alert_type: Optional - Filter by type (misinformation, broken_link, outdated)
        severity: Optional - Filter by severity (low, medium, high, critical)
        status: Optional - Filter by status (new, reviewed, resolved, dismissed)
        page: Optional - Page number (default: 1)
        page_size: Optional - Items per page (default: 20, max: 100)
    """
    domain_id = request.query_params.get('domain_id')

    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    alerts = MisinformationAlert.objects.filter(domain_id=domain_id)

    # Apply filters
    alert_type = request.query_params.get('alert_type')
    if alert_type:
        # Support comma-separated values
        types = [t.strip() for t in alert_type.split(',')]
        alerts = alerts.filter(alert_type__in=types)

    severity = request.query_params.get('severity')
    if severity:
        # Support comma-separated values
        severities = [s.strip() for s in severity.split(',')]
        alerts = alerts.filter(severity__in=severities)

    alert_status = request.query_params.get('status')
    if alert_status:
        # Support comma-separated values
        statuses = [s.strip() for s in alert_status.split(',')]
        alerts = alerts.filter(status__in=statuses)

    # Pagination
    page = int(request.query_params.get('page', 1))
    page_size = min(int(request.query_params.get('page_size', 20)), 100)
    start = (page - 1) * page_size
    end = start + page_size

    total = alerts.count()
    alerts = alerts.order_by('-created_at')[start:end]

    serializer = MisinformationAlertListSerializer(alerts, many=True)

    return Response({
        'total': total,
        'page': page,
        'page_size': page_size,
        'results': serializer.data
    })


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def alert_detail(request, alert_id):
    """
    Get or update a misinformation alert.

    GET: Get alert details
    PATCH: Update alert status
    """
    try:
        alert = MisinformationAlert.objects.select_related(
            'domain', 'prompt', 'citation_url', 'reviewed_by'
        ).get(id=alert_id)
    except MisinformationAlert.DoesNotExist:
        return Response(
            {'error': 'Alert not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        serializer = MisinformationAlertDetailSerializer(alert)
        return Response(serializer.data)

    elif request.method == 'PATCH':
        serializer = MisinformationAlertUpdateSerializer(alert, data=request.data, partial=True)
        if serializer.is_valid():
            # Set reviewed_by and reviewed_at
            alert.reviewed_by = request.user
            alert.reviewed_at = timezone.now()
            serializer.save()
            return Response(MisinformationAlertDetailSerializer(alert).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_scan(request):
    """
    Trigger a manual misinformation scan.

    Body:
        domain_id: Required - ID of the domain to scan
        prompt_analytics_ids: Optional - List of specific prompt analytics IDs to scan
    """
    serializer = TriggerScanSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    domain_id = serializer.validated_data['domain_id']
    prompt_analytics_ids = serializer.validated_data.get('prompt_analytics_ids')

    try:
        domain = Domain.objects.get(id=domain_id)
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check for running scan
    running_scan = MisinformationScan.objects.filter(
        domain=domain,
        status='running'
    ).first()

    if running_scan:
        return Response(
            {
                'error': 'A scan is already running for this domain',
                'scan_id': running_scan.id
            },
            status=status.HTTP_409_CONFLICT
        )

    # Check if domain has any prompt analytics with citations to scan
    has_data = PromptAnalytics.objects.filter(
        prompt__group__domain_id=domain_id,
        track_status='COMP',
        is_mention=True
    ).exists()

    if not has_data:
        # Update domain status to NOT_READY
        domain.misinformation_scan_status = 'NOT_READY'
        domain.save(update_fields=['misinformation_scan_status'])
        return Response(
            {
                'error': 'No prompt data available for scanning. Please wait for prompts to be tracked first.',
                'status': 'NOT_READY'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Domain has data, update status to READY if not already scanning
    if domain.misinformation_scan_status == 'NOT_READY':
        domain.misinformation_scan_status = 'READY'
        domain.save(update_fields=['misinformation_scan_status'])

    try:
        # Call engine API to start misinformation scan
        engine_api_url = getattr(settings, 'ENGINE_API_URL', 'http://localhost:8001').rstrip('/')
        scan_endpoint = f"{engine_api_url}/api/misinformation/scan/"
        
        payload = {
            'domain_id': domain_id
        }
        if prompt_analytics_ids:
            payload['prompt_analytics_ids'] = prompt_analytics_ids
        
        response = requests.post(
            scan_endpoint,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 202:
            # Scan started successfully
            return Response(
                {
                    'status': 'started',
                    'message': 'Misinformation scan started in engine',
                    'task_id': response.json().get('task_id'),
                    'domain_id': domain_id
                },
                status=status.HTTP_202_ACCEPTED
            )
        elif response.status_code == 409:
            # Scan already running
            return Response(
                response.json(),
                status=status.HTTP_409_CONFLICT
            )
        else:
            # Error from engine
            error_data = response.json() if response.content else {'error': 'Unknown error'}
            logger.error(f"Engine API error: {error_data}")
            return Response(
                error_data,
                status=response.status_code
            )
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling engine API: {e}")
        return Response(
            {'error': f'Failed to connect to engine: {str(e)}'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"Error triggering scan: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def scan_status(request, scan_id):
    """
    Get the status of a misinformation scan.
    """
    try:
        scan = MisinformationScan.objects.get(id=scan_id)
    except MisinformationScan.DoesNotExist:
        return Response(
            {'error': 'Scan not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = MisinformationScanSerializer(scan)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def scan_list(request):
    """
    List misinformation scans for a domain.

    Query params:
        domain_id: Required - ID of the domain
        page: Optional - Page number
        page_size: Optional - Items per page
    """
    domain_id = request.query_params.get('domain_id')

    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    scans = MisinformationScan.objects.filter(domain_id=domain_id)

    # Pagination
    page = int(request.query_params.get('page', 1))
    page_size = min(int(request.query_params.get('page_size', 20)), 100)
    start = (page - 1) * page_size
    end = start + page_size

    total = scans.count()
    scans = scans.order_by('-created_at')[start:end]

    serializer = MisinformationScanSerializer(scans, many=True)

    return Response({
        'total': total,
        'page': page,
        'page_size': page_size,
        'results': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics(request):
    """
    Get misinformation analytics/trends.

    Query params:
        domain_id: Required - ID of the domain
        start_date: Optional - Start date (YYYY-MM-DD)
        end_date: Optional - End date (YYYY-MM-DD)
        period: Optional - daily, weekly, monthly (default: daily)
    """
    domain_id = request.query_params.get('domain_id')

    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Default date range: last 30 days
    end_date = request.query_params.get('end_date')
    start_date = request.query_params.get('start_date')

    if end_date:
        end_date = date.fromisoformat(end_date)
    else:
        end_date = date.today()

    if start_date:
        start_date = date.fromisoformat(start_date)
    else:
        start_date = end_date - timedelta(days=30)

    analytics_data = MisinformationAnalytics.objects.filter(
        domain_id=domain_id,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')

    serializer = MisinformationAnalyticsSerializer(analytics_data, many=True)

    # Calculate summary
    summary = analytics_data.aggregate(
        total_detected=Sum('total_detected'),
        broken_links=Sum('broken_links_count'),
        misinformation=Sum('misinformation_count'),
        outdated=Sum('outdated_count'),
    )

    return Response({
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'summary': summary,
        'data': serializer.data
    })


# ======================= Citations API Views =======================

def extract_domain_from_url(url):
    """Extract domain name from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc or parsed.path.split('/')[0]
    except:
        return url


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def citations_dashboard(request):
    """
    Get citations dashboard summary with metrics.
    Reads directly from PromptAnalytics.citation_list.

    Query params:
        domain_id: Required - ID of the domain
        days: Optional - Number of days (default: 30)
    """
    domain_id = request.query_params.get('domain_id')
    days = int(request.query_params.get('days', 30))

    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        domain = Domain.objects.get(id=domain_id)
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    start_date = timezone.now() - timedelta(days=days)

    # Get all completed prompt analytics
    all_analytics = PromptAnalytics.objects.filter(
        prompt__group__domain=domain,
        track_status='COMP'
    )

    recent_analytics = all_analytics.filter(created_at__gte=start_date)

    # Extract all URLs from citation_list
    all_urls = []
    url_to_analytics_map = {}  # Track which analytics has which URL
    domain_url_clean = domain.url.replace('https://', '').replace('http://', '').rstrip('/')

    for pa in all_analytics:
        if pa.citation_list and isinstance(pa.citation_list, list):
            for url in pa.citation_list:
                all_urls.append({
                    'url': url,
                    'platform': pa.platform,
                    'created_at': pa.created_at,
                    'prompt_analytics_id': pa.id
                })
                if url not in url_to_analytics_map:
                    url_to_analytics_map[url] = []
                url_to_analytics_map[url].append(pa)

    # Total citations count
    total_citations = len(all_urls)

    # Unique sources (unique domains from URLs)
    unique_sources = set()
    for url_data in all_urls:
        unique_sources.add(extract_domain_from_url(url_data['url']))
    unique_sources_count = len(unique_sources)

    # Your domain citations (citations pointing to your domain)
    your_domain_citations = sum(1 for url_data in all_urls if domain_url_clean in url_data['url'])

    # Competitor citations
    competitor_citations = total_citations - your_domain_citations

    # Citation rate (% of prompts with citations)
    total_prompts = all_analytics.count()
    prompts_with_citations = all_analytics.exclude(citation_list=[]).count()
    citation_rate = round((prompts_with_citations / total_prompts * 100), 1) if total_prompts > 0 else 0

    # Average citations per response
    total_citation_count = sum(len(pa.citation_list) if pa.citation_list else 0 for pa in all_analytics)
    avg_citations_per_response = round(total_citation_count / total_prompts, 1) if total_prompts > 0 else 0

    # For crawl status, check CitationURL table if data exists
    crawled_urls = CitationURL.objects.filter(domain=domain)
    broken_links = crawled_urls.filter(
        Q(http_status_code__gte=400) | Q(crawl_status='failed')
    ).count()

    # New sources in last 7 days
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_urls = [u for u in all_urls if u['created_at'] >= seven_days_ago]
    new_sources_7d = len(set(extract_domain_from_url(u['url']) for u in recent_urls))

    # Status breakdown (only if misinformation scan has run)
    status_breakdown = {
        'valid': crawled_urls.filter(crawl_status='success', http_status_code__lt=400).count(),
        'broken': broken_links,
        'pending': total_citations - crawled_urls.count(),  # URLs not yet crawled
        'blocked': crawled_urls.filter(crawl_status='blocked').count(),
    }

    # Citations by platform
    platform_breakdown = {}
    for url_data in all_urls:
        platform = url_data['platform']
        platform_breakdown[platform] = platform_breakdown.get(platform, 0) + 1

    # Citations trend (last N days)
    trend_data = []
    for i in range(days):
        day = timezone.now().date() - timedelta(days=days - i - 1)
        day_count = sum(1 for u in all_urls if u['created_at'].date() == day)
        trend_data.append({
            'date': day.isoformat(),
            'count': day_count
        })

    # Top cited domains
    domain_counts = Counter(extract_domain_from_url(u['url']) for u in all_urls)
    top_domains = [{'domain': d, 'count': c} for d, c in domain_counts.most_common(10)]

    if not top_domains:
        try:
            from seo_rankings.services import datablue_service
            raw = datablue_service.fetch_one(keyword_text=domain.name)
            if raw:
                counts = {}
                for item in (raw.get('organic_results') or []):
                    host = extract_domain_from_url(item.get('link') or item.get('url') or '')
                    if host and domain.name.lower() not in host.lower():
                        counts[host] = counts.get(host, 0) + 1
                if counts:
                    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
                    top_domains = [{'domain': h, 'count': c} for h, c in ranked]
        except Exception as e:
            logger.debug(f"DataBlue dashboard fallback notice: {e}")

    return Response({
        'summary': {
            'total_citations': total_citations,
            'unique_sources': unique_sources_count,
            'your_domain_citations': your_domain_citations,
            'competitor_citations': competitor_citations,
            'citation_rate': citation_rate,
            'avg_citations_per_response': avg_citations_per_response,
            'broken_links': broken_links,
            'new_sources_7d': new_sources_7d,
        },
        'status_breakdown': status_breakdown,
        'platform_breakdown': platform_breakdown,
        'trend_data': trend_data,
        'top_domains': top_domains,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def citations_list(request):
    """
    List all citations with filtering and pagination.
    Reads directly from PromptAnalytics.citation_list.

    Query params:
        domain_id: Required - ID of the domain
        source_type: Optional - your_domain, competitor, third_party
        platform: Optional - Filter by AI platform
        search: Optional - Search in URL
        page: Optional - Page number (default: 1)
        page_size: Optional - Items per page (default: 20, max: 100)
    """
    domain_id = request.query_params.get('domain_id')

    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        domain = Domain.objects.get(id=domain_id)
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Get pagination params early
    page = int(request.query_params.get('page', 1))
    page_size = min(int(request.query_params.get('page_size', 20)), 100)

    # Get filters
    platform = request.query_params.get('platform')
    source_type_filter = request.query_params.get('source_type')
    search = request.query_params.get('search')
    status_filter = request.query_params.get('status')

    # Build optimized query with select_related for performance
    # Note: We use select_related to avoid N+1 queries when accessing prompt and group
    analytics_qs = PromptAnalytics.objects.filter(
        prompt__group__domain=domain,
        track_status='COMP'
    ).exclude(citation_list=[]).order_by('-created_at')

    # Platform filter at DB level
    if platform and platform.lower() != 'all':
        clean_platform = platform.lower().replace('google ', '')
        analytics_qs = analytics_qs.filter(platform__icontains=clean_platform)

    # Extract all citations with metadata
    all_citations = []
    domain_url_clean = domain.url.replace('https://', '').replace('http://', '').rstrip('/')

    def _norm_url(u):
        if not u:
            return ''
        u = u.strip()
        return u[:-1] if u.endswith('/') else u

    # Pre-fetch all citation URLs for this domain to avoid N+1 queries
    citation_urls_map = {}
    for citation_url in CitationURL.objects.filter(domain=domain).only('url', 'crawl_status', 'http_status_code'):
        citation_urls_map[citation_url.url] = citation_url
        norm = _norm_url(citation_url.url)
        if norm:
            citation_urls_map[norm] = citation_url

    # Process analytics in batches and use early exit strategy
    # We'll stop fetching once we have enough results for the current page
    batch_size = 100
    offset = 0
    target_citations = page * page_size + 50  # Fetch a bit extra to account for filtering

    while offset < 10000:  # Allow scanning up to 10,000 analytics records for filtered results
        batch = analytics_qs[offset:offset + batch_size]
        if not batch:
            break

        for pa in batch:
            if pa.citation_list and isinstance(pa.citation_list, list):
                for idx, url in enumerate(pa.citation_list):
                    # Early search filter check (fastest filter)
                    if search and search.lower() not in url.lower():
                        continue

                    source_domain = extract_domain_from_url(url)
                    is_your_domain = domain_url_clean in url

                    # Source type filter
                    if source_type_filter:
                        if source_type_filter == 'your_domain' and not is_your_domain:
                            continue
                        elif source_type_filter == 'third_party' and is_your_domain:
                            continue

                    # Check if this URL has been crawled (from pre-fetched map)
                    crawled_citation = citation_urls_map.get(url) or citation_urls_map.get(_norm_url(url))

                    display_status = 'pending'
                    http_status_code = None
                    crawl_status = 'pending'

                    if crawled_citation:
                        crawl_status = crawled_citation.crawl_status
                        http_status_code = crawled_citation.http_status_code

                        if crawl_status == 'success' and http_status_code and http_status_code < 400:
                            display_status = 'valid'
                        elif crawl_status == 'blocked':
                            # Check blocked BEFORE the >=400 branch: blocked citations
                            # carry http_status_code=403, so the generic >=400 test
                            # would otherwise mis-map them to 'broken'.
                            display_status = 'blocked'
                        elif (http_status_code and http_status_code >= 400) or crawl_status in ('failed', 'broken'):
                            display_status = 'broken'

                    # Status filter - support both 'valid'/'success' and 'broken'/'failed'
                    if status_filter and status_filter.lower() != 'all':
                        sf = status_filter.lower()
                        if sf in ('success', 'valid'):
                            if display_status not in ('valid', 'success'):
                                continue
                        elif sf in ('failed', 'broken'):
                            if display_status not in ('broken', 'failed'):
                                continue
                        elif display_status != sf:
                            continue

                    all_citations.append({
                        'url': url,
                        'source_domain': source_domain,
                        'is_your_domain': is_your_domain,
                        'source_type': 'your_domain' if is_your_domain else 'third_party',
                        'platform': pa.platform,
                        'created_at': pa.created_at,
                        'prompt_analytics_id': pa.id,
                        'display_status': display_status,
                        'crawl_status': crawl_status,
                        'http_status_code': http_status_code,
                        'position_in_response': idx + 1,
                        'context_snippet': None,
                    })

        # Early exit if we have enough citations for current page
        if len(all_citations) >= target_citations:
            break

        offset += batch_size

    # Sort by created_at descending (citations are already roughly sorted by analytics order)
    all_citations.sort(key=lambda x: x['created_at'], reverse=True)

    # Pagination
    start = (page - 1) * page_size
    end = start + page_size

    total = len(all_citations)
    results = all_citations[start:end]

    # Group by URL to get mention counts
    url_mention_counts = Counter(c['url'] for c in all_citations)
    for result in results:
        result['mention_count'] = url_mention_counts[result['url']]

    return Response({
        'total': total,
        'page': page,
        'page_size': page_size,
        'results': results
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def citations_by_source(request):
    """
    Get citations grouped by source domain.
    Reads directly from PromptAnalytics.citation_list.

    Query params:
        domain_id: Required - ID of the domain
        limit: Optional - Number of sources to return (default: 20)
    """
    domain_id = request.query_params.get('domain_id')
    limit = int(request.query_params.get('limit', 20))

    if not domain_id:
        return Response(
            {'error': 'domain_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        domain = Domain.objects.get(id=domain_id)
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    domain_url_clean = domain.url.replace('https://', '').replace('http://', '').rstrip('/')

    # Get all completed prompt analytics
    all_analytics = PromptAnalytics.objects.filter(
        prompt__group__domain=domain,
        track_status='COMP'
    ).exclude(citation_list=[])

    # Extract and group by source domain
    source_data = {}

    for pa in all_analytics:
        if pa.citation_list and isinstance(pa.citation_list, list):
            for url in pa.citation_list:
                source = extract_domain_from_url(url)

                if source not in source_data:
                    source_data[source] = {
                        'source_domain': source,
                        'mention_count': 0,
                        'is_your_domain': domain_url_clean in url,
                        'platforms': set(),
                        'last_cited': None,
                    }

                source_data[source]['mention_count'] += 1
                source_data[source]['platforms'].add(pa.platform)

                if not source_data[source]['last_cited'] or pa.created_at > source_data[source]['last_cited']:
                    source_data[source]['last_cited'] = pa.created_at

    # Convert to list and format
    results = []
    for source, data in source_data.items():
        data['platforms'] = list(data['platforms'])
        results.append(data)

    if not results:
        try:
            from seo_rankings.services import datablue_service
            raw = datablue_service.fetch_one(keyword_text=domain.name)
            if raw:
                counts = {}
                for item in (raw.get('organic_results') or []):
                    host = extract_domain_from_url(item.get('link') or item.get('url') or '')
                    if host and domain.name.lower() not in host.lower():
                        counts[host] = counts.get(host, 0) + 1
                if counts:
                    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
                    results = [{
                        'source_domain': h,
                        'mention_count': c,
                        'is_your_domain': domain_url_clean in h,
                        'platforms': ['DataBlue SERP'],
                        'last_cited': timezone.now()
                    } for h, c in ranked]
        except Exception as e:
            logger.debug(f"DataBlue citations_by_source fallback notice: {e}")

    # Sort by mention_count
    results.sort(key=lambda x: x['mention_count'], reverse=True)

    return Response({
        'total': len(results),
        'results': results[:limit]
    })



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def citation_detail(request, citation_id):
    """
    Get detailed information about a specific citation.
    """
    try:
        citation = CitationURL.objects.select_related(
            'domain', 'prompt_analytics', 'content'
        ).get(id=citation_id)
    except CitationURL.DoesNotExist:
        return Response(
            {'error': 'Citation not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    domain_url = citation.domain.url.replace('https://', '').replace('http://', '').rstrip('/')
    source_domain = extract_domain_from_url(citation.url)
    is_your_domain = domain_url in citation.url

    # Get related alerts for this citation
    related_alerts = MisinformationAlert.objects.filter(
        citation_url=citation
    ).values('id', 'alert_type', 'severity', 'status', 'created_at')

    # Get all mentions (using new CitationMention model) for this citation
    mentions = CitationMention.objects.filter(
        citation_url=citation
    ).select_related('prompt_analytics').order_by('-mentioned_at')

    mentions_count = mentions.count()

    # Build mentions timeline data
    mentions_timeline = []
    for mention in mentions[:20]:  # Limit to most recent 20 mentions
        mentions_timeline.append({
            'id': mention.id,
            'mentioned_at': mention.mentioned_at,
            'context_snippet': mention.context_snippet[:300] if mention.context_snippet else None,
            'position_in_response': mention.position_in_response,
            'is_primary_source': mention.is_primary_source,
            'platform': mention.prompt_analytics.platform if mention.prompt_analytics else None,
            'prompt_id': mention.prompt_analytics.prompt_id if mention.prompt_analytics else None,
        })

    # Get platforms where this URL was mentioned
    platforms_mentioned = list(set(m.prompt_analytics.platform for m in mentions if m.prompt_analytics))

    data = {
        'id': citation.id,
        'url': citation.url,
        'source_domain': source_domain,
        'is_your_domain': is_your_domain,
        'source_type': 'your_domain' if is_your_domain else 'third_party',
        'crawl_status': citation.crawl_status,
        'http_status_code': citation.http_status_code,
        'crawl_error': citation.crawl_error,
        'last_crawled_at': citation.last_crawled_at,
        'created_at': citation.created_at,
        'content': {
            'page_title': citation.content.page_title if hasattr(citation, 'content') and citation.content else None,
            'meta_description': citation.content.meta_description if hasattr(citation, 'content') and citation.content else None,
            'publish_date': citation.content.publish_date if hasattr(citation, 'content') and citation.content else None,
            'extracted_text': citation.content.extracted_text[:500] if hasattr(citation, 'content') and citation.content and citation.content.extracted_text else None,
        } if hasattr(citation, 'content') and citation.content else None,
        'prompt_analytics': {
            'id': citation.prompt_analytics.id,
            'platform': citation.prompt_analytics.platform,
            'prompt_text': citation.prompt_analytics.prompt.prompt if citation.prompt_analytics.prompt else None,
            'context_summary': citation.prompt_analytics.context_summary,
        } if citation.prompt_analytics else None,
        'related_alerts': list(related_alerts),
        'mentions_count': mentions_count,
        'platforms_mentioned': platforms_mentioned,
        'mentions_timeline': mentions_timeline,
    }

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def alert_full_comparison(request, alert_id):
    """
    Get full comparison data for a misinformation alert.
    Returns the complete LLM response and full source content for detailed comparison.

    Returns:
        - Alert details
        - Full prompt text
        - Full LLM response (context_summary from prompt_analytics)
        - Full source content (extracted_text from citation_content)
        - Citation URL details
    """
    try:
        alert = MisinformationAlert.objects.select_related(
            'domain', 'prompt', 'prompt_analytics', 'citation_url'
        ).get(id=alert_id)
    except MisinformationAlert.DoesNotExist:
        return Response(
            {'error': 'Alert not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Get full LLM response from prompt_analytics
    llm_response = None
    prompt_text = None
    platform = None

    if alert.prompt_analytics:
        llm_response = alert.prompt_analytics.context_summary
        platform = alert.prompt_analytics.platform

    if alert.prompt:
        prompt_text = alert.prompt.prompt

    # Get full source content from citation_content
    source_content_full = None
    page_title = None
    meta_description = None
    source_url = None
    crawl_status = None

    if alert.citation_url:
        source_url = alert.citation_url.url
        crawl_status = alert.citation_url.crawl_status

        # Get the CitationContent
        try:
            citation_content = CitationContent.objects.get(citation_url=alert.citation_url)
            source_content_full = citation_content.extracted_text
            page_title = citation_content.page_title
            meta_description = citation_content.meta_description
        except CitationContent.DoesNotExist:
            pass

    data = {
        'alert': {
            'id': alert.id,
            'alert_type': alert.alert_type,
            'severity': alert.severity,
            'status': alert.status,
            'llm_claim': alert.llm_claim,
            'source_content_snippet': alert.source_content,
            'explanation': alert.explanation,
            'created_at': alert.created_at,
        },
        'prompt': {
            'id': alert.prompt.id if alert.prompt else None,
            'text': prompt_text,
        },
        'llm_response': {
            'platform': platform,
            'full_response': llm_response,
        },
        'source': {
            'url': source_url,
            'crawl_status': crawl_status,
            'page_title': page_title,
            'meta_description': meta_description,
            'full_content': source_content_full,
        },
    }

    return Response(data)

