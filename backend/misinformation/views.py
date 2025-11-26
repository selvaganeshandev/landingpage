"""
API Views for Misinformation Module
"""
import logging
from datetime import date, timedelta
from django.db.models import Sum, Count
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
)
from .serializers import (
    MisinformationAlertListSerializer,
    MisinformationAlertDetailSerializer,
    MisinformationAlertUpdateSerializer,
    MisinformationScanSerializer,
    MisinformationAnalyticsSerializer,
    DashboardSerializer,
    TriggerScanSerializer,
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
