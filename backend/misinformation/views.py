"""
API Views for Misinformation Module
"""
import logging
from datetime import date, timedelta
from urllib.parse import urlparse
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
from .tasks import run_misinformation_scan

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
        scan = run_misinformation_scan(domain_id, prompt_analytics_ids)
        return Response(
            MisinformationScanSerializer(scan).data,
            status=status.HTTP_201_CREATED
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

    # Get all citation URLs for the domain
    all_citations = CitationURL.objects.filter(domain=domain)
    recent_citations = all_citations.filter(created_at__gte=start_date)

    # Total citations count
    total_citations = all_citations.count()

    # Unique sources (unique domains from URLs)
    unique_sources = set()
    for citation in all_citations.values_list('url', flat=True):
        unique_sources.add(extract_domain_from_url(citation))
    unique_sources_count = len(unique_sources)

    # Your domain citations (citations pointing to your domain)
    domain_url = domain.url.replace('https://', '').replace('http://', '').rstrip('/')
    your_domain_citations = all_citations.filter(
        Q(url__icontains=domain_url)
    ).count()

    # Competitor citations (would need competitor data - placeholder for now)
    competitor_citations = 0

    # Citation rate (% of prompts with citations)
    total_prompts = PromptAnalytics.objects.filter(
        prompt__group__domain=domain,
        track_status='COMP'
    ).count()
    prompts_with_citations = PromptAnalytics.objects.filter(
        prompt__group__domain=domain,
        track_status='COMP',
        total_citations__gt=0
    ).count()
    citation_rate = round((prompts_with_citations / total_prompts * 100), 1) if total_prompts > 0 else 0

    # Average citations per response
    avg_citations = PromptAnalytics.objects.filter(
        prompt__group__domain=domain,
        track_status='COMP'
    ).aggregate(avg=Sum('total_citations'))['avg'] or 0
    avg_citations_per_response = round(avg_citations / total_prompts, 1) if total_prompts > 0 else 0

    # Broken links count
    broken_links = all_citations.filter(
        Q(http_status_code__gte=400) | Q(crawl_status='failed')
    ).count()

    # New sources in last 7 days
    seven_days_ago = timezone.now() - timedelta(days=7)
    new_sources_7d = all_citations.filter(created_at__gte=seven_days_ago).count()

    # Status breakdown
    status_breakdown = {
        'valid': all_citations.filter(crawl_status='success', http_status_code__lt=400).count(),
        'broken': broken_links,
        'pending': all_citations.filter(crawl_status='pending').count(),
        'blocked': all_citations.filter(crawl_status='blocked').count(),
    }

    # Citations by platform
    platform_breakdown = {}
    for pa in PromptAnalytics.objects.filter(
        prompt__group__domain=domain,
        track_status='COMP',
        total_citations__gt=0
    ).values('platform').annotate(count=Sum('total_citations')):
        platform_breakdown[pa['platform']] = pa['count']

    # Citations trend (last N days)
    trend_data = []
    for i in range(days):
        day = timezone.now().date() - timedelta(days=days - i - 1)
        day_count = all_citations.filter(
            created_at__date=day
        ).count()
        trend_data.append({
            'date': day.isoformat(),
            'count': day_count
        })

    # Top cited domains
    domain_counts = {}
    for url in all_citations.values_list('url', flat=True):
        source_domain = extract_domain_from_url(url)
        domain_counts[source_domain] = domain_counts.get(source_domain, 0) + 1

    top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]

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
        'top_domains': [{'domain': d, 'count': c} for d, c in top_domains],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def citations_list(request):
    """
    List all citations with filtering and pagination.

    Query params:
        domain_id: Required - ID of the domain
        status: Optional - Filter by crawl_status (pending, success, failed, blocked)
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

    citations = CitationURL.objects.filter(domain=domain).select_related(
        'prompt_analytics', 'content'
    )

    # Apply filters
    crawl_status = request.query_params.get('status')
    if crawl_status:
        statuses = [s.strip() for s in crawl_status.split(',')]
        citations = citations.filter(crawl_status__in=statuses)

    # Source type filter
    source_type = request.query_params.get('source_type')
    if source_type:
        domain_url = domain.url.replace('https://', '').replace('http://', '').rstrip('/')
        if source_type == 'your_domain':
            citations = citations.filter(url__icontains=domain_url)
        elif source_type == 'third_party':
            citations = citations.exclude(url__icontains=domain_url)

    # Platform filter
    platform = request.query_params.get('platform')
    if platform:
        citations = citations.filter(prompt_analytics__platform=platform)

    # Search filter
    search = request.query_params.get('search')
    if search:
        citations = citations.filter(url__icontains=search)

    # Pagination
    page = int(request.query_params.get('page', 1))
    page_size = min(int(request.query_params.get('page_size', 20)), 100)
    start = (page - 1) * page_size
    end = start + page_size

    total = citations.count()
    citations = citations.order_by('-created_at')[start:end]

    # Build response data with additional computed fields
    results = []
    domain_url = domain.url.replace('https://', '').replace('http://', '').rstrip('/')

    for citation in citations:
        source_domain = extract_domain_from_url(citation.url)
        is_your_domain = domain_url in citation.url

        # Determine status
        if citation.crawl_status == 'success' and citation.http_status_code and citation.http_status_code < 400:
            display_status = 'valid'
        elif citation.http_status_code and citation.http_status_code >= 400:
            display_status = 'broken'
        elif citation.crawl_status == 'blocked':
            display_status = 'blocked'
        elif citation.crawl_status == 'failed':
            display_status = 'failed'
        else:
            display_status = 'pending'

        # Get mention count and latest context snippet using CitationMention
        mention_count = CitationMention.objects.filter(citation_url=citation).count()
        latest_mention = CitationMention.objects.filter(
            citation_url=citation
        ).order_by('-mentioned_at').first()

        context_snippet = None
        if latest_mention and latest_mention.context_snippet:
            context_snippet = latest_mention.context_snippet[:300]

        results.append({
            'id': citation.id,
            'url': citation.url,
            'source_domain': source_domain,
            'crawl_status': citation.crawl_status,
            'http_status_code': citation.http_status_code,
            'display_status': display_status,
            'is_your_domain': is_your_domain,
            'source_type': 'your_domain' if is_your_domain else 'third_party',
            'platform': citation.prompt_analytics.platform if citation.prompt_analytics else None,
            'page_title': citation.content.page_title if hasattr(citation, 'content') and citation.content else None,
            'last_crawled_at': citation.last_crawled_at,
            'created_at': citation.created_at,
            'prompt_analytics_id': citation.prompt_analytics_id,
            # New enriched fields from CitationMention
            'mention_count': mention_count,
            'context_snippet': context_snippet,
            'last_mentioned_at': latest_mention.mentioned_at if latest_mention else citation.created_at,
        })

    return Response({
        'total': total,
        'page': page,
        'page_size': page_size,
        'results': results
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
def citations_by_source(request):
    """
    Get citations grouped by source domain.

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

    domain_url = domain.url.replace('https://', '').replace('http://', '').rstrip('/')

    # Group by source domain using CitationMention for accurate counts
    citations = CitationURL.objects.filter(domain=domain).select_related('prompt_analytics')

    domain_data = {}
    for citation in citations:
        source = extract_domain_from_url(citation.url)
        if source not in domain_data:
            domain_data[source] = {
                'source_domain': source,
                'citation_count': 0,
                'mention_count': 0,  # Total mentions using CitationMention
                'valid_count': 0,
                'broken_count': 0,
                'is_your_domain': domain_url in citation.url,
                'platforms': set(),
                'last_cited': None,
            }

        domain_data[source]['citation_count'] += 1

        # Get actual mention count from CitationMention table
        mention_count = CitationMention.objects.filter(citation_url=citation).count()
        domain_data[source]['mention_count'] += mention_count if mention_count else 1

        if citation.crawl_status == 'success' and (not citation.http_status_code or citation.http_status_code < 400):
            domain_data[source]['valid_count'] += 1
        elif citation.http_status_code and citation.http_status_code >= 400:
            domain_data[source]['broken_count'] += 1

        if citation.prompt_analytics:
            domain_data[source]['platforms'].add(citation.prompt_analytics.platform)

        # Get latest mention date
        latest_mention = CitationMention.objects.filter(citation_url=citation).order_by('-mentioned_at').first()
        citation_date = latest_mention.mentioned_at if latest_mention else citation.created_at

        if not domain_data[source]['last_cited'] or citation_date > domain_data[source]['last_cited']:
            domain_data[source]['last_cited'] = citation_date

    # Convert to list and sort
    results = []
    for source, data in domain_data.items():
        data['platforms'] = list(data['platforms'])
        results.append(data)

    # Sort by mention_count (actual mentions) rather than just citation_count
    results.sort(key=lambda x: x['mention_count'], reverse=True)

    return Response({
        'total': len(results),
        'results': results[:limit]
    })
