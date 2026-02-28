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
