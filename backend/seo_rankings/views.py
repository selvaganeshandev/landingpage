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
from .models import (
    SeoKeywordRank, SeoRankHistory, SeoSerpFeatureHistory, SeoDomainDailyMetrics,
    SeoCompetitorAnalysis, SeoCompetitorProject, SeoCompetitorKeyword,
)
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

    # Compute SERP Features & Google Ads on-the-fly from keyword data
    # (matches RankMax's ProjectOverviewSerializer approach — always fresh)
    all_keywords = SeoKeywordRank.objects.filter(domain_id=domain_id)
    rating_0_2 = 0
    rating_2_4 = 0
    rating_4_5 = 0
    ads_you_above_below = 0
    ads_you_above = 0
    ads_you_below = 0
    ads_others_above_below = 0
    ads_others_above = 0
    ads_others_below = 0

    for kw in all_keywords:
        # Rating buckets (matches RankMax isfloat_isdigit + R2/R4/R5)
        rating = 0
        if kw.total_rating and kw.total_rating != '-':
            try:
                rating = int(kw.total_rating) if kw.total_rating.isdigit() else float(kw.total_rating)
            except (ValueError, TypeError):
                rating = 0
        if rating <= 2:
            rating_0_2 += 1
        elif rating <= 4:
            rating_2_4 += 1
        elif rating <= 5:
            rating_4_5 += 1

        # Google Ads (matches RankMax Ay/Ao logic)
        snippets = kw.snippets_details or {}
        if kw.ads and 'ads' in snippets:
            ads_data = snippets['ads']
            top_count = int(ads_data.get('top_count', 0) or 0)
            bottom_count = int(ads_data.get('bottom_count', 0) or 0)
            ads_status = ads_data.get('status', 'no')

            if top_count > 0 and bottom_count > 0:
                if ads_status == 'yes':
                    ads_you_above_below += 1
                else:
                    ads_others_above_below += 1
            elif top_count > 0:
                if ads_status == 'yes':
                    ads_you_above += 1
                else:
                    ads_others_above += 1
            elif bottom_count > 0:
                if ads_status == 'yes':
                    ads_you_below += 1
                else:
                    ads_others_below += 1

    today_data = SeoDomainDailyMetricsSerializer(latest).data if latest else None
    # Override rating/ads fields with fresh computed values
    if today_data:
        today_data['rating_0_2'] = rating_0_2
        today_data['rating_2_4'] = rating_2_4
        today_data['rating_4_5'] = rating_4_5
        today_data['ads_you_above_below'] = ads_you_above_below
        today_data['ads_you_above'] = ads_you_above
        today_data['ads_you_below'] = ads_you_below
        today_data['ads_others_above_below'] = ads_others_above_below
        today_data['ads_others_above'] = ads_others_above
        today_data['ads_others_below'] = ads_others_below

    data = {
        'today': today_data,
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_refresh_status(request):
    """
    Check refresh progress for a domain.
    Query params: domain_id (required)
    Returns: total keywords, completed count, running count, progress %, and status.
    Ported from RankMax /refreshstatus endpoint.
    """
    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_ids = list(_get_user_domain_ids(request.user))
    if int(domain_id) not in allowed_ids:
        return Response({'error': 'Domain not found or access denied'}, status=status.HTTP_403_FORBIDDEN)

    total = SeoKeywordRank.objects.filter(domain_id=domain_id).count()
    if total == 0:
        return Response({
            'refreshing': False,
            'total': 0,
            'completed': 0,
            'running': 0,
            'progress': 0,
            'status': 'idle',
        })

    done_count = SeoKeywordRank.objects.filter(
        domain_id=domain_id,
        auto_call_status__in=['done', 'fail'],
    ).count()
    running_count = SeoKeywordRank.objects.filter(
        domain_id=domain_id,
        auto_call_status__in=['avail', 'busy', 'load', 'read'],
    ).count()

    is_refreshing = running_count > 0
    progress = int((done_count / total) * 100) if total > 0 else 0

    return Response({
        'refreshing': is_refreshing,
        'total': total,
        'completed': done_count,
        'running': running_count,
        'progress': progress,
        'status': 'running' if is_refreshing else 'done',
    })


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


# ---------------------------------------------------------------------------
# Bulk Delete (ported from RankMax /multidelete)
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seo_keyword_bulk_delete(request):
    """
    Delete multiple SEO keywords and their related history.
    Body: { ids: [1, 2, 3] }
    """
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only admins can delete keywords'}, status=status.HTTP_403_FORBIDDEN)

    ids = request.data.get('ids', [])
    if not ids:
        return Response({'error': 'ids list is required'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_ids = list(_get_user_domain_ids(request.user))

    # Only delete keywords belonging to user's domains
    keywords_to_delete = SeoKeywordRank.objects.filter(
        pk__in=ids,
        domain_id__in=allowed_ids,
    )
    count = keywords_to_delete.count()

    if count == 0:
        return Response({'error': 'No matching keywords found'}, status=status.HTTP_404_NOT_FOUND)

    # Related history is cascade-deleted via FK
    keywords_to_delete.delete()

    return Response({
        'status': 'true',
        'message': f'{count} keyword(s) deleted successfully',
        'deleted_count': count,
    })


# ---------------------------------------------------------------------------
# Tag Management (ported from RankMax /update_tags, /remove_tag)
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seo_keyword_update_tags(request):
    """
    Bulk update tags for selected keywords.
    Body: { ids: [1,2,3], tags: ["tag1","tag2"], mode: "merge"|"replace" }
    mode=merge (default): adds tags to existing ones.
    mode=replace: replaces all tags.
    Max 20 tags per keyword.
    """
    ids = request.data.get('ids', [])
    new_tags = request.data.get('tags', [])
    mode = request.data.get('mode', 'merge')

    if not ids:
        return Response({'error': 'ids list is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Sanitise: lowercase, strip, deduplicate
    new_tags = list(set(t.strip().lower() for t in new_tags if t.strip()))

    allowed_ids = list(_get_user_domain_ids(request.user))
    keywords = SeoKeywordRank.objects.filter(pk__in=ids, domain_id__in=allowed_ids)

    updated = 0
    for kw in keywords:
        if mode == 'replace':
            kw.tags = new_tags[:20]
        else:
            merged = list(set((kw.tags or []) + new_tags))[:20]
            kw.tags = merged
        kw.save(update_fields=['tags'])
        updated += 1

    return Response({
        'status': 'true',
        'message': f'Tags updated for {updated} keyword(s)',
        'updated_count': updated,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seo_keyword_remove_tag(request):
    """
    Remove a specific tag from all keywords in a domain.
    Body: { domain_id: 50, tag: "tagname" }
    """
    domain_id = request.data.get('domain_id')
    tag_name = request.data.get('tag', '').strip().lower()

    if not domain_id or not tag_name:
        return Response({'error': 'domain_id and tag are required'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_ids = list(_get_user_domain_ids(request.user))
    if int(domain_id) not in allowed_ids:
        return Response({'error': 'Domain not found or access denied'}, status=status.HTTP_403_FORBIDDEN)

    keywords = SeoKeywordRank.objects.filter(
        domain_id=domain_id,
        tags__contains=[tag_name],
    )

    updated = 0
    for kw in keywords:
        if tag_name in kw.tags:
            kw.tags.remove(tag_name)
            kw.save(update_fields=['tags'])
            updated += 1

    return Response({
        'status': 'true',
        'message': f'Tag "{tag_name}" removed from {updated} keyword(s)',
        'updated_count': updated,
    })


# ---------------------------------------------------------------------------
# Favourite Toggle (ported from RankMax /favour)
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seo_keyword_toggle_favourite(request):
    """
    Toggle favourite status for one or all keywords.
    Body: { id: 123, value: 1 }      — single keyword
    Body: { domain_id: 50, value: 1 } — all keywords in domain
    value: 1 = favourite, 0 = unfavourite
    """
    kw_id = request.data.get('id')
    domain_id = request.data.get('domain_id')
    value = int(request.data.get('value', 0))

    allowed_ids = list(_get_user_domain_ids(request.user))

    if kw_id:
        # Single keyword
        try:
            kw = SeoKeywordRank.objects.get(pk=kw_id, domain_id__in=allowed_ids)
        except SeoKeywordRank.DoesNotExist:
            return Response({'error': 'Keyword not found'}, status=status.HTTP_404_NOT_FOUND)

        kw.favour = value
        kw.save(update_fields=['favour'])
        msg = 'Keyword marked as favourite.' if value else 'Keyword removed from favourites.'

    elif domain_id:
        # All keywords in domain
        if int(domain_id) not in allowed_ids:
            return Response({'error': 'Domain not found or access denied'}, status=status.HTTP_403_FORBIDDEN)

        SeoKeywordRank.objects.filter(domain_id=domain_id).update(favour=value)
        msg = 'All keywords marked as favourite.' if value else 'All keywords removed from favourites.'

    else:
        return Response({'error': 'id or domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'status': 'true', 'message': msg})


# ---------------------------------------------------------------------------
# Get Tags for Domain (for tag management UI)
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_keyword_get_tags(request):
    """
    Get all unique tags used in a domain, plus common tags for selected keywords.
    Query params: domain_id (required), ids (optional, comma-separated keyword IDs)
    """
    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_ids = list(_get_user_domain_ids(request.user))
    if int(domain_id) not in allowed_ids:
        return Response({'error': 'Domain not found or access denied'}, status=status.HTTP_403_FORBIDDEN)

    # All tags in domain
    all_tags_lists = SeoKeywordRank.objects.filter(
        domain_id=domain_id,
    ).exclude(tags=[]).values_list('tags', flat=True)

    all_tags = set()
    for tag_list in all_tags_lists:
        all_tags.update(t.lower() for t in tag_list)

    # Common tags for selected keywords
    ids_str = request.query_params.get('ids', '')
    common_tags = []
    if ids_str:
        kw_ids = [int(i) for i in ids_str.split(',') if i.strip()]
        if kw_ids:
            selected_kws = SeoKeywordRank.objects.filter(pk__in=kw_ids, domain_id=domain_id)
            tag_sets = [set(kw.tags or []) for kw in selected_kws]
            if tag_sets:
                common_tags = list(set.intersection(*tag_sets)) if tag_sets else []

    return Response({
        'all_tags': sorted(all_tags),
        'common_tags': sorted(common_tags),
    })


# ---------------------------------------------------------------------------
# PDF Export (WeasyPrint — same approach as Rankmaxx /pdfexport)
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seo_pdf_export(request):
    """
    Generate a PDF report for all keywords in a domain.
    Body: { domain_id: number }
    Returns: PDF binary (application/octet-stream)
    """
    from weasyprint import HTML
    from django.template.loader import render_to_string
    from django.http import HttpResponse
    from urllib.parse import urlparse
    from datetime import datetime
    import base64
    import os

    domain_id = request.data.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_ids = list(_get_user_domain_ids(request.user))
    if int(domain_id) not in allowed_ids:
        return Response({'error': 'Domain not found or access denied'}, status=status.HTTP_403_FORBIDDEN)

    try:
        domain = Domain.objects.get(pk=domain_id)
    except Domain.DoesNotExist:
        return Response({'error': 'Domain not found'}, status=status.HTTP_404_NOT_FOUND)

    # Fetch keywords sorted: ranked first (ascending), unranked at end
    raw_keywords = list(
        SeoKeywordRank.objects.filter(domain_id=domain_id)
        .select_related('keyword')
        .order_by('rank_now')
    )
    keywords_sorted = sorted(
        raw_keywords,
        key=lambda x: x.rank_now if x.rank_now > 0 else float('inf')
    )

    def get_domain_slug(url):
        if not url:
            return ''
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.replace('www.', '')
            path = parsed.path
            if path in ('', '/'):
                return netloc
            return netloc + path
        except Exception:
            return url

    def compute_competition(volume):
        if volume is None:
            return '(NA)'
        if volume < 1000:
            return 'Low'
        if volume < 10000:
            return 'Med'
        return 'High'

    kw_data = []
    for kw in keywords_sorted:
        kw_data.append({
            'keyword': kw.keyword.keyword if kw.keyword else '',
            'rank_now': kw.rank_now,
            'top_rank': kw.top_rank or 0,
            'day_val': abs(kw.day_val),
            'day_mark': kw.day_mark,
            'week_val': abs(kw.week_val),
            'week_mark': kw.week_mark,
            'search_volume': kw.search_volume,
            'comp': compute_competition(kw.search_volume),
            'site_url': kw.site_url or domain.url or '',
            'domain_slug': get_domain_slug(kw.site_url or domain.url or ''),
            'region': kw.region or '',
            'created_date': kw.created_at.strftime('%b %d, %Y') if kw.created_at else '',
        })

    report_date = datetime.now().strftime('%B %d, %Y')

    # Embed logo as base64 so WeasyPrint doesn't need the frontend running
    logo_base64 = ''
    logo_path = settings.BASE_DIR.parent / 'frontend' / 'public' / 'logo.png'
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            logo_base64 = base64.b64encode(f.read()).decode('utf-8')

    html_content = render_to_string('seo_rankings/seo_pdf_report.html', {
        'keywords': kw_data,
        'projectname': domain.name,
        'domainurl': domain.url,
        'reportdate': report_date,
        'logo_base64': logo_base64,
    })

    pdf_bytes = HTML(string=html_content).write_pdf()
    return HttpResponse(pdf_bytes, content_type='application/octet-stream')


# ---------------------------------------------------------------------------
# SEO Competitor Analysis
# ---------------------------------------------------------------------------

# Domains to exclude from competitor results
_COMP_EXCLUDE = {
    'google.com', 'google.co.uk', 'google.co.in', 'google.com.au',
    'youtube.com', 'facebook.com', 'twitter.com', 'instagram.com',
    'linkedin.com', 'pinterest.com', 'reddit.com', 'tiktok.com',
    'wikipedia.org', 'amazon.com', 'ebay.com', 'bing.com', 'yahoo.com',
    'quora.com', 'tumblr.com', 'wordpress.com', 'blogger.com',
    'wix.com', 'squarespace.com', 'shopify.com',
}


def _run_competitor_analysis(domain_id: int):
    """
    Background thread: aggregate competitor domains from SERP data.
    Data sources (tried in order per keyword):
      1. snippets_details['competitors']  — rank-keyed dict set by parser_service / engine
      2. SeoSerpFeatureHistory.comp_today — {tp:[…], bf:[…], ar:[…]} set by scraping_service
      3. Fresh single-page ScrapingDog call (page 0 = top ~10 results)
    Updates SeoCompetitorAnalysis to COMP or FAIL.
    """
    import requests as http_requests
    from urllib.parse import urlparse
    from django.db import connection

    SCRAPINGDOG_URL = "https://api.scrapingdog.com/google"

    def _extract_dom(url):
        try:
            p = urlparse(url if '://' in url else f'https://{url}')
            return (p.netloc or p.path).lower().replace('www.', '').split('/')[0]
        except Exception:
            return ''

    try:
        # Get project domain for self-exclusion
        domain_obj = Domain.objects.get(id=domain_id)
        project_domain_clean = (domain_obj.url or '').lower()
        project_domain_clean = (
            project_domain_clean
            .replace('https://', '').replace('http://', '')
            .replace('www.', '').split('/')[0]
        )

        keywords = list(
            SeoKeywordRank.objects.filter(domain_id=domain_id)
            .select_related('keyword')
        )
        total_kw = len(keywords)
        api_key = getattr(settings, 'SCRAPINGDOG_API_KEY', '') or ''

        # Pre-load SeoSerpFeatureHistory comp_today for all keywords (single query)
        serp_history_map = {}
        serp_histories = SeoSerpFeatureHistory.objects.filter(
            seo_keyword_rank_id__in=[kw.id for kw in keywords]
        ).values_list('seo_keyword_rank_id', 'comp_today')
        for kw_id, comp_today in serp_histories:
            if comp_today and isinstance(comp_today, dict):
                serp_history_map[kw_id] = comp_today

        domain_counts = {}   # {competitor_domain: hit_count}
        domain_kw_ids = {}   # {competitor_domain: [kw_ids]}
        fresh_calls = 0

        for kw in keywords:
            # --- Source 1: snippets_details['competitors'] (rank-keyed dict) ---
            competitors = {}
            if kw.snippets_details and isinstance(kw.snippets_details, dict):
                competitors = kw.snippets_details.get('competitors', {})

            # --- Source 2: SeoSerpFeatureHistory.comp_today ---
            # Two formats: rank-keyed dict (from engine) or {tp,bf,ar} segments (from backend)
            if not competitors:
                comp_today = serp_history_map.get(kw.id, {})
                if comp_today:
                    # Check if it's rank-keyed format: {'1': {url, domain, rank}, '2': ...}
                    first_key = next(iter(comp_today), None)
                    if first_key and first_key not in ('tp', 'bf', 'ar'):
                        # Rank-keyed format from engine
                        for rk, cd in comp_today.items():
                            if isinstance(cd, dict) and cd.get('domain'):
                                competitors[str(rk)] = {
                                    'url': cd.get('url', ''),
                                    'domain': cd.get('domain', ''),
                                    'rank': cd.get('rank', 0),
                                }
                    else:
                        # {tp:[{rn,dn,lk},...], bf:[...], ar:[...]} format from backend
                        for segment_key in ('tp', 'bf', 'ar'):
                            segment = comp_today.get(segment_key, [])
                            if isinstance(segment, list):
                                for item in segment:
                                    if isinstance(item, dict):
                                        rn = item.get('rn', '')
                                        dn = item.get('dn', '')
                                        lk = item.get('lk', '')
                                        if rn and dn:
                                            competitors[str(rn)] = {
                                                'url': lk,
                                                'domain': dn,
                                                'rank': int(rn) if str(rn).isdigit() else 0,
                                            }
                    # Cache into snippets_details for future analyses
                    if competitors:
                        sd = kw.snippets_details if isinstance(kw.snippets_details, dict) else {}
                        sd['competitors'] = competitors
                        SeoKeywordRank.objects.filter(id=kw.id).update(snippets_details=sd)

            # --- Source 3: Fresh ScrapingDog single-page call ---
            if not competitors and api_key:
                kw_text = kw.keyword.keyword if kw.keyword else ''
                if kw_text:
                    try:
                        params = {
                            'api_key': api_key,
                            'query': kw_text,
                            'country': kw.isocode or 'us',
                            'language': kw.language_code or 'en',
                            'domain': kw.region or 'google.com',
                            'page': 0,
                            'advance_search': 'false',
                        }
                        if kw.geo_target_uule:
                            params['uule'] = kw.geo_target_uule

                        resp = http_requests.get(
                            SCRAPINGDOG_URL, params=params, timeout=(3.05, 15)
                        )
                        fresh_calls += 1

                        if resp.status_code == 200:
                            page_json = resp.json()
                            if isinstance(page_json, dict):
                                for item in page_json.get('organic_results', []):
                                    if not isinstance(item, dict):
                                        continue
                                    item_url = item.get('link', '')
                                    item_domain = _extract_dom(item_url)
                                    item_rank = item.get('rank') or item.get('position', 0)
                                    try:
                                        item_rank = int(item_rank)
                                    except (ValueError, TypeError):
                                        item_rank = 0
                                    if item_rank and item_domain:
                                        competitors[str(item_rank)] = {
                                            'url': item_url,
                                            'domain': item_domain,
                                            'rank': item_rank,
                                        }

                                # Cache back into DB
                                if competitors:
                                    sd = kw.snippets_details if isinstance(kw.snippets_details, dict) else {}
                                    sd['competitors'] = competitors
                                    SeoKeywordRank.objects.filter(id=kw.id).update(snippets_details=sd)

                    except Exception as e:
                        logger.warning(f"[CompAnalysis] SERP fetch error for '{kw_text}': {e}")

            # Tally competitor domains
            for _rank_str, comp_data in competitors.items():
                if not isinstance(comp_data, dict):
                    continue
                comp_d = comp_data.get('domain', '').lower().replace('www.', '')
                if not comp_d:
                    continue
                if project_domain_clean and (
                    comp_d == project_domain_clean
                    or project_domain_clean in comp_d
                    or comp_d in project_domain_clean
                ):
                    continue
                if comp_d in _COMP_EXCLUDE:
                    continue

                domain_counts[comp_d] = domain_counts.get(comp_d, 0) + 1
                domain_kw_ids.setdefault(comp_d, []).append(kw.id)

        # Sort by frequency, keep top 100
        sorted_domains = dict(
            sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:100]
        )

        SeoCompetitorAnalysis.objects.filter(
            domain_id=domain_id, status='SCHD'
        ).update(
            status='COMP',
            total_keywords=total_kw,
            unique_domains=len(sorted_domains),
            total_domain_hits=sum(sorted_domains.values()) if sorted_domains else 0,
            analysis_json={'domains': sorted_domains, 'keys': domain_kw_ids},
        )
        logger.info(
            f"[CompAnalysis] Domain {domain_id}: {total_kw} kw → "
            f"{len(sorted_domains)} competitors ({fresh_calls} fresh calls)"
        )

    except Exception as e:
        logger.error(f"[CompAnalysis] Error for domain {domain_id}: {e}", exc_info=True)
        SeoCompetitorAnalysis.objects.filter(
            domain_id=domain_id, status='SCHD'
        ).update(status='FAIL')
    finally:
        connection.close()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seo_competitor_start(request):
    """
    Start competitor analysis for a domain.
    Body: { domain_id: int }
    Runs analysis in a background thread (reads stored SERP data + fresh calls).
    """
    import threading

    domain_id = request.data.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id required'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_ids = list(_get_user_domain_ids(request.user))
    if int(domain_id) not in allowed_ids:
        return Response({'error': 'Domain not found or access denied'}, status=status.HTTP_403_FORBIDDEN)

    # If already running, return current status
    existing = SeoCompetitorAnalysis.objects.filter(domain_id=domain_id).first()
    if existing and existing.status == 'SCHD':
        return Response({'status': 'SCHD', 'id': existing.id})

    # Create or reset analysis record
    if existing:
        existing.status = 'SCHD'
        existing.total_keywords = 0
        existing.unique_domains = 0
        existing.total_domain_hits = 0
        existing.analysis_json = {}
        existing.save()
        analysis = existing
    else:
        analysis = SeoCompetitorAnalysis.objects.create(domain_id=int(domain_id), status='SCHD')

    # Run analysis in background thread (no engine/Celery dependency)
    t = threading.Thread(
        target=_run_competitor_analysis,
        args=(int(domain_id),),
        daemon=True,
    )
    t.start()

    return Response({'status': 'SCHD', 'id': analysis.id})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_competitor_status(request):
    """
    Get competitor analysis status for a domain.
    Query params: domain_id (required)
    Returns status + candidate list when COMP.
    """
    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id required'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_ids = list(_get_user_domain_ids(request.user))
    if int(domain_id) not in allowed_ids:
        return Response({'error': 'Domain not found or access denied'}, status=status.HTTP_403_FORBIDDEN)

    analysis = SeoCompetitorAnalysis.objects.filter(domain_id=domain_id).first()
    if not analysis:
        return Response({'status': 'INIT'})

    data = {
        'status': analysis.status,
        'id': analysis.id,
        'total_keywords': analysis.total_keywords,
        'unique_domains': analysis.unique_domains,
        'total_domain_hits': analysis.total_domain_hits,
    }

    if analysis.status == 'COMP':
        domains = analysis.analysis_json.get('domains', {})
        sorted_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:100]

        projects = SeoCompetitorProject.objects.filter(domain_id=domain_id)
        tracked_set = {p.competitor_domain for p in projects}

        data['candidates'] = [
            {'domain': d, 'count': c, 'tracked': d in tracked_set}
            for d, c in sorted_domains
        ]
        data['tracked_count'] = len(tracked_set)

    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seo_competitor_add(request):
    """
    Add a competitor domain to track.
    Body: { domain_id: int, competitor_domain: str }
    Max 6 competitors per domain.
    """
    domain_id = request.data.get('domain_id')
    competitor_domain = request.data.get('competitor_domain', '').strip().lower()
    competitor_domain = competitor_domain.replace('www.', '')

    if not domain_id or not competitor_domain:
        return Response({'error': 'domain_id and competitor_domain required'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_ids = list(_get_user_domain_ids(request.user))
    if int(domain_id) not in allowed_ids:
        return Response({'error': 'Domain not found or access denied'}, status=status.HTTP_403_FORBIDDEN)

    existing_count = SeoCompetitorProject.objects.filter(domain_id=domain_id).count()
    if existing_count >= 6:
        return Response({'error': 'Maximum 6 competitors allowed'}, status=status.HTTP_400_BAD_REQUEST)

    project, created = SeoCompetitorProject.objects.get_or_create(
        domain_id=int(domain_id),
        competitor_domain=competitor_domain,
    )

    if created:
        _build_competitor_keywords(int(domain_id), project)

    return Response({
        'id': project.id,
        'competitor_domain': project.competitor_domain,
        'created': created,
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


def _build_competitor_keywords(domain_id, project):
    """
    Build SeoCompetitorKeyword rows from stored competitor data.
    Reads from snippets_details['competitors'] first, falls back to
    SeoSerpFeatureHistory.comp_today for existing keywords.
    """
    competitor_domain = project.competitor_domain
    keywords = list(SeoKeywordRank.objects.filter(domain_id=domain_id).select_related('keyword'))

    # Pre-load SeoSerpFeatureHistory comp_today
    serp_history_map = {}
    serp_histories = SeoSerpFeatureHistory.objects.filter(
        seo_keyword_rank_id__in=[kw.id for kw in keywords]
    ).values_list('seo_keyword_rank_id', 'comp_today')
    for kw_id, comp_today in serp_histories:
        if comp_today and isinstance(comp_today, dict):
            serp_history_map[kw_id] = comp_today

    rows = []
    for kw in keywords:
        our_rank = kw.rank_now
        our_url = kw.site_url or ''
        their_rank = 0
        their_url = ''

        # Source 1: snippets_details['competitors']
        competitors = kw.snippets_details.get('competitors', {}) if kw.snippets_details else {}

        # Source 2: SeoSerpFeatureHistory.comp_today (rank-keyed or {tp,bf,ar} format)
        if not competitors:
            comp_today = serp_history_map.get(kw.id, {})
            if comp_today:
                first_key = next(iter(comp_today), None)
                if first_key and first_key not in ('tp', 'bf', 'ar'):
                    for rk, cd in comp_today.items():
                        if isinstance(cd, dict) and cd.get('domain'):
                            competitors[str(rk)] = {
                                'url': cd.get('url', ''),
                                'domain': cd.get('domain', ''),
                                'rank': cd.get('rank', 0),
                            }
                else:
                    for segment_key in ('tp', 'bf', 'ar'):
                        segment = comp_today.get(segment_key, [])
                        if isinstance(segment, list):
                            for item in segment:
                                if isinstance(item, dict):
                                    rn = item.get('rn', '')
                                    dn = item.get('dn', '')
                                    lk = item.get('lk', '')
                                    if rn and dn:
                                        competitors[str(rn)] = {
                                            'url': lk,
                                            'domain': dn,
                                            'rank': int(rn) if str(rn).isdigit() else 0,
                                        }

        for _rank_str, comp_data in competitors.items():
            if isinstance(comp_data, dict):
                comp_d = comp_data.get('domain', '')
                if comp_d and (competitor_domain in comp_d or comp_d in competitor_domain):
                    their_rank = comp_data.get('rank', 0)
                    their_url = comp_data.get('url', '')
                    break

        keyword_text = kw.keyword.keyword if kw.keyword else ''
        rows.append(SeoCompetitorKeyword(
            domain_id=domain_id,
            competitor=project,
            seo_keyword_rank=kw,
            keyword_text=keyword_text,
            our_rank=our_rank,
            their_rank=their_rank,
            our_url=our_url,
            their_url=their_url,
        ))

    SeoCompetitorKeyword.objects.filter(competitor=project).delete()
    if rows:
        SeoCompetitorKeyword.objects.bulk_create(rows, ignore_conflicts=True)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def seo_competitor_delete(request, pk):
    """Remove a competitor project."""
    allowed_ids = list(_get_user_domain_ids(request.user))
    try:
        project = SeoCompetitorProject.objects.get(id=pk)
    except SeoCompetitorProject.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if project.domain_id not in allowed_ids:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    project.delete()
    return Response({'success': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_competitor_projects(request):
    """
    List competitor projects for a domain.
    Query params: domain_id (required)
    """
    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id required'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_ids = list(_get_user_domain_ids(request.user))
    if int(domain_id) not in allowed_ids:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    projects = SeoCompetitorProject.objects.filter(domain_id=domain_id)
    data = []
    for p in projects:
        kw_count = p.keywords.count()
        ranked_us = p.keywords.filter(our_rank__gt=0).count()
        ranked_them = p.keywords.filter(their_rank__gt=0).count()
        data.append({
            'id': p.id,
            'competitor_domain': p.competitor_domain,
            'keyword_count': kw_count,
            'ranked_us': ranked_us,
            'ranked_them': ranked_them,
            'created_at': p.created_at.isoformat(),
        })

    return Response({'projects': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_competitor_keywords(request, pk):
    """
    Get keyword rank comparison for a competitor project.
    """
    allowed_ids = list(_get_user_domain_ids(request.user))
    try:
        project = SeoCompetitorProject.objects.get(id=pk)
    except SeoCompetitorProject.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if project.domain_id not in allowed_ids:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    kws = SeoCompetitorKeyword.objects.filter(
        competitor=project
    ).select_related('seo_keyword_rank').order_by('our_rank', 'keyword_text')

    data = []
    for kw in kws:
        skr = kw.seo_keyword_rank  # Related SeoKeywordRank with full ranking data
        row = {
            'id': kw.id,
            'keyword': kw.keyword_text,
            'our_rank': kw.our_rank,
            'their_rank': kw.their_rank,
            'our_url': kw.our_url,
            'their_url': kw.their_url,
            'best_rank': 0,
            'search_volume': None,
            'last_ranked_date': None,
            'featured_snippet': False,
            'knowledge_panel': False,
            'ads': False,
        }
        if skr:
            row['best_rank'] = skr.top_rank or 0
            row['search_volume'] = skr.search_volume
            row['last_ranked_date'] = skr.last_ranked_date
            row['featured_snippet'] = skr.featured_snippet or False
            row['knowledge_panel'] = skr.knowledge_panel or False
            row['ads'] = skr.ads or False
        data.append(row)

    return Response({
        'competitor_domain': project.competitor_domain,
        'keywords': data,
    })
