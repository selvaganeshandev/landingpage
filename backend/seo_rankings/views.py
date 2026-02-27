"""
SEO Rankings — API views.
All endpoints are org-scoped via request.user.organisation → Domain access.
"""
import logging
from datetime import date

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.conf import settings

from domains.models import Domain
from .models import SeoKeywordRank, SeoRankHistory, SeoSerpFeatureHistory, SeoDomainDailyMetrics
from .serializers import (
    SeoKeywordRankSerializer,
    SeoKeywordRankCreateSerializer,
    SeoRankHistorySerializer,
    SeoSerpFeatureHistorySerializer,
    SeoDomainDailyMetricsSerializer,
)

logger = logging.getLogger(__name__)


def _get_user_domain_ids(user):
    """Get domain IDs the user has access to (org-scoped)."""
    if user.role == 'super_admin':
        return Domain.objects.filter(
            organisation=user.organisation
        ).values_list('id', flat=True)
    else:
        from domains.models import DomainAccess
        return DomainAccess.objects.filter(
            user=user,
            domain__organisation=user.organisation
        ).values_list('domain_id', flat=True)


# ---------------------------------------------------------------------------
# Keyword Rankings CRUD
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_keyword_list(request):
    """
    List SEO keyword rankings for a domain.
    Query params: domain_id (required), platform (optional), status (optional)
    """
    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Verify domain access
    allowed_ids = list(_get_user_domain_ids(request.user))
    if int(domain_id) not in allowed_ids:
        return Response({'error': 'Domain not found or access denied'}, status=status.HTTP_403_FORBIDDEN)

    qs = SeoKeywordRank.objects.filter(domain_id=domain_id).select_related('keyword', 'domain')

    # Optional filters
    platform = request.query_params.get('platform')
    if platform in ('desktop', 'mobile'):
        qs = qs.filter(platform=platform)

    call_status = request.query_params.get('status')
    if call_status:
        qs = qs.filter(auto_call_status=call_status)

    search = request.query_params.get('search')
    if search:
        qs = qs.filter(keyword__keyword__icontains=search)

    qs = qs.order_by('-rank_now')
    serializer = SeoKeywordRankSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seo_keyword_add(request):
    """
    Add a keyword to SEO rank tracking.
    Body: { keyword, domain, platform, target_url, region, isocode, language_code, ... }
    """
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only admins can add SEO keywords'}, status=status.HTTP_403_FORBIDDEN)

    serializer = SeoKeywordRankCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    domain = serializer.validated_data['domain']
    if domain.organisation != request.user.organisation:
        return Response({'error': 'Domain not in your organisation'}, status=status.HTTP_403_FORBIDDEN)

    try:
        with transaction.atomic():
            seo_kw = serializer.save(auto_call_status='avail')
        return Response(
            SeoKeywordRankSerializer(seo_kw).data,
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seo_keyword_bulk_add(request):
    """
    Bulk-add keywords to SEO tracking.
    Body: { domain_id, keywords: [{ keyword_id, platform, target_url, region, isocode, language_code }] }
    """
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only admins can add SEO keywords'}, status=status.HTTP_403_FORBIDDEN)

    domain_id = request.data.get('domain_id')
    keywords_data = request.data.get('keywords', [])

    if not domain_id or not keywords_data:
        return Response({'error': 'domain_id and keywords list required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        domain = Domain.objects.get(pk=domain_id, organisation=request.user.organisation)
    except Domain.DoesNotExist:
        return Response({'error': 'Domain not found'}, status=status.HTTP_404_NOT_FOUND)

    created = []
    skipped = []

    with transaction.atomic():
        for kw_data in keywords_data:
            keyword_id = kw_data.get('keyword_id')
            if not keyword_id:
                skipped.append({'keyword_id': keyword_id, 'reason': 'missing keyword_id'})
                continue

            platform = kw_data.get('platform', 'desktop')
            obj, was_created = SeoKeywordRank.objects.get_or_create(
                keyword_id=keyword_id,
                domain=domain,
                platform=platform,
                defaults={
                    'target_url': kw_data.get('target_url', ''),
                    'region': kw_data.get('region', 'google.com'),
                    'isocode': kw_data.get('isocode', 'us'),
                    'language_code': kw_data.get('language_code', 'en'),
                    'geo_target': kw_data.get('geo_target', ''),
                    'geo_target_uule': kw_data.get('geo_target_uule', ''),
                    'auto_call_status': 'avail',
                }
            )
            if was_created:
                created.append(SeoKeywordRankSerializer(obj).data)
            else:
                skipped.append({'keyword_id': keyword_id, 'reason': 'already exists'})

    return Response({
        'created_count': len(created),
        'skipped_count': len(skipped),
        'created': created[:10],
        'skipped': skipped,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def seo_keyword_detail(request, pk):
    """Get or delete a single SEO keyword rank entry."""
    allowed_ids = list(_get_user_domain_ids(request.user))

    try:
        seo_kw = SeoKeywordRank.objects.select_related('keyword', 'domain').get(pk=pk, domain_id__in=allowed_ids)
    except SeoKeywordRank.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(SeoKeywordRankSerializer(seo_kw).data)

    if request.method == 'DELETE':
        if request.user.role not in ['admin', 'super_admin']:
            return Response({'error': 'Only admins can delete'}, status=status.HTTP_403_FORBIDDEN)
        seo_kw.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Rank History
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_rank_history(request, seo_kw_id):
    """
    Get rank history for a specific keyword.
    Query params: days (optional, default 30)
    """
    allowed_ids = list(_get_user_domain_ids(request.user))

    try:
        seo_kw = SeoKeywordRank.objects.get(pk=seo_kw_id, domain_id__in=allowed_ids)
    except SeoKeywordRank.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    days = int(request.query_params.get('days', 30))
    from datetime import timedelta
    since = date.today() - timedelta(days=days)

    history = SeoRankHistory.objects.filter(
        seo_keyword_rank=seo_kw,
        snapshot_date__gte=since,
    ).order_by('snapshot_date')

    serializer = SeoRankHistorySerializer(history, many=True)
    return Response(serializer.data)


# ---------------------------------------------------------------------------
# SERP Feature History
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_serp_features(request, seo_kw_id):
    """Get SERP feature history for a keyword."""
    allowed_ids = list(_get_user_domain_ids(request.user))

    try:
        seo_kw = SeoKeywordRank.objects.get(pk=seo_kw_id, domain_id__in=allowed_ids)
    except SeoKeywordRank.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    history = SeoSerpFeatureHistory.objects.filter(seo_keyword_rank=seo_kw)
    serializer = SeoSerpFeatureHistorySerializer(history, many=True)
    return Response(serializer.data)


# ---------------------------------------------------------------------------
# Domain Metrics
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_domain_metrics(request):
    """
    Get domain-level SEO metrics.
    Query params: domain_id (required), days (optional, default 30)
    """
    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_ids = list(_get_user_domain_ids(request.user))
    if int(domain_id) not in allowed_ids:
        return Response({'error': 'Domain not found or access denied'}, status=status.HTTP_403_FORBIDDEN)

    days = int(request.query_params.get('days', 30))
    from datetime import timedelta
    since = date.today() - timedelta(days=days)

    metrics = SeoDomainDailyMetrics.objects.filter(
        domain_id=domain_id,
        snapshot_date__gte=since,
    ).order_by('-snapshot_date')

    serializer = SeoDomainDailyMetricsSerializer(metrics, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_domain_overview(request):
    """
    Get the latest domain overview: today's metrics + comparison data.
    Query params: domain_id (required)
    """
    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_ids = list(_get_user_domain_ids(request.user))
    if int(domain_id) not in allowed_ids:
        return Response({'error': 'Domain not found or access denied'}, status=status.HTTP_403_FORBIDDEN)

    today = date.today()

    # Latest metrics
    latest = SeoDomainDailyMetrics.objects.filter(
        domain_id=domain_id
    ).order_by('-snapshot_date').first()

    # Yesterday's metrics for comparison
    from datetime import timedelta
    yesterday = SeoDomainDailyMetrics.objects.filter(
        domain_id=domain_id,
        snapshot_date__lt=today,
    ).order_by('-snapshot_date').first()

    # Best metrics ever
    best = SeoDomainDailyMetrics.objects.filter(
        domain_id=domain_id
    ).order_by('-score_meter').first()

    data = {
        'today': SeoDomainDailyMetricsSerializer(latest).data if latest else None,
        'yesterday': SeoDomainDailyMetricsSerializer(yesterday).data if yesterday else None,
        'best': SeoDomainDailyMetricsSerializer(best).data if best else None,
        'comparison': [],
    }

    if latest:
        data['comparison'] = [
            {
                'status': 'Top 1',
                'today': latest.top_1_count,
                'yesterday': yesterday.top_1_count if yesterday else 0,
                'best': best.top_1_count if best else 0,
            },
            {
                'status': 'Top 3',
                'today': latest.top_3_count,
                'yesterday': yesterday.top_3_count if yesterday else 0,
                'best': best.top_3_count if best else 0,
            },
            {
                'status': 'Top 10',
                'today': latest.top_10_count,
                'yesterday': yesterday.top_10_count if yesterday else 0,
                'best': best.top_10_count if best else 0,
            },
            {
                'status': 'Top 50',
                'today': latest.top_50_count,
                'yesterday': yesterday.top_50_count if yesterday else 0,
                'best': best.top_50_count if best else 0,
            },
            {
                'status': 'Top 100',
                'today': latest.top_100_count,
                'yesterday': yesterday.top_100_count if yesterday else 0,
                'best': best.top_100_count if best else 0,
            },
            {
                'status': 'Not Ranked',
                'today': latest.not_ranked_count,
                'yesterday': yesterday.not_ranked_count if yesterday else 0,
                'best': best.not_ranked_count if best else 0,
            },
        ]

    return Response(data)


# ---------------------------------------------------------------------------
# Engine Trigger
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seo_trigger_ranking(request):
    """
    Trigger SEO ranking process for a domain.
    Body: { domain_id } or { seo_keyword_rank_id } for single keyword.
    Dispatches to Celery via the engine API.
    """
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only admins can trigger ranking'}, status=status.HTTP_403_FORBIDDEN)

    domain_id = request.data.get('domain_id')
    seo_kw_id = request.data.get('seo_keyword_rank_id')

    if not domain_id and not seo_kw_id:
        return Response(
            {'error': 'Provide domain_id or seo_keyword_rank_id'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    allowed_ids = list(_get_user_domain_ids(request.user))

    if seo_kw_id:
        # Single keyword trigger
        try:
            seo_kw = SeoKeywordRank.objects.get(pk=seo_kw_id, domain_id__in=allowed_ids)
        except SeoKeywordRank.DoesNotExist:
            return Response({'error': 'Keyword not found'}, status=status.HTTP_404_NOT_FOUND)

        # Call engine API to trigger single keyword
        import requests as http_requests
        engine_url = getattr(settings, 'ENGINE_API_URL', 'http://localhost:8001')
        try:
            resp = http_requests.post(
                f'{engine_url}/api/seo/process-keyword/',
                json={'seo_keyword_rank_id': seo_kw.id},
                timeout=10,
            )
            return Response({'message': 'Keyword ranking triggered', 'engine_status': resp.status_code})
        except http_requests.RequestException as e:
            logger.error(f"Engine API call failed: {e}")
            return Response(
                {'error': 'Engine service unavailable', 'detail': str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    else:
        # Domain-level trigger
        if int(domain_id) not in allowed_ids:
            return Response({'error': 'Domain not found'}, status=status.HTTP_403_FORBIDDEN)

        # Auto-seed: if no SEO keywords exist for this domain, create them from existing keywords
        seeded_count = 0
        if not SeoKeywordRank.objects.filter(domain_id=domain_id).exists():
            from keywords.models import Keyword
            domain_keywords = Keyword.objects.filter(domain_id=domain_id)
            seo_kw_objects = []
            for kw in domain_keywords:
                seo_kw_objects.append(SeoKeywordRank(
                    keyword=kw,
                    domain_id=int(domain_id),
                    platform='desktop',
                    auto_call_status='avail',
                ))
            if seo_kw_objects:
                SeoKeywordRank.objects.bulk_create(seo_kw_objects, ignore_conflicts=True)
                seeded_count = len(seo_kw_objects)
                logger.info(f"Auto-seeded {seeded_count} keywords for domain {domain_id}")

        # Reset keyword statuses to avail
        SeoKeywordRank.objects.filter(
            domain_id=domain_id,
            auto_call_status__in=['done', 'fail']
        ).update(auto_call_status='avail')

        import requests as http_requests
        engine_url = getattr(settings, 'ENGINE_API_URL', 'http://localhost:8001')
        try:
            resp = http_requests.post(
                f'{engine_url}/api/seo/process-domain/',
                json={'domain_id': int(domain_id)},
                timeout=10,
            )
            msg = 'Domain ranking triggered'
            if seeded_count:
                msg = f'{seeded_count} keywords auto-added and ranking triggered'
            return Response({'message': msg, 'engine_status': resp.status_code, 'seeded': seeded_count})
        except http_requests.RequestException as e:
            logger.error(f"Engine API call failed: {e}")
            return Response(
                {'error': 'Engine service unavailable', 'detail': str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
