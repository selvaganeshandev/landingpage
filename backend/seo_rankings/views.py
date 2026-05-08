"""
SEO Rankings — API views.
All endpoints are org-scoped via request.user.organisation → Domain access.
"""
import logging
from datetime import date, timedelta

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
    SeoReportSheet, SeoKeywordNote, SeoKeywordVolume,
)
from .serializers import (
    SeoKeywordRankSerializer,
    SeoKeywordRankCreateSerializer,
    SeoRankHistorySerializer,
    SeoSerpFeatureHistorySerializer,
    SeoDomainDailyMetricsSerializer,
    SeoKeywordNoteSerializer,
    SeoKeywordNoteCreateSerializer,
    SeoKeywordVolumeSerializer,
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
def seo_keyword_remaining(request):
    """
    Return the remaining keyword quota for the user's organisation.
    Response: { limit, used, remaining }
    """
    org = request.user.organisation
    limit = org.seo_keyword_limit if org else 3000
    used = SeoKeywordRank.objects.filter(
        domain__organisation=org
    ).count()
    return Response({
        'limit': limit,
        'used': used,
        'remaining': max(0, limit - used),
    })


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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seo_keyword_import(request):
    """
    Import keywords from an external source (e.g. RankMaxx CSV export) into
    both the Keyword table and SEO tracking in a single call.

    Accepts keyword text strings directly — no need to pre-create Keyword
    objects or know their IDs.  Does NOT trigger domain processing or change
    domain.processing_status, so existing prompt-generation flows are
    unaffected.

    Body (JSON):
    {
        "domain_id": 123,
        "platform": "desktop",          // optional, default "desktop"
        "region": "google.co.in",       // optional, default "google.com"
        "isocode": "in",                // optional, default "us"
        "language_code": "en",          // optional, default "en"
        "geo_target": "",               // optional
        "geo_target_uule": "",          // optional
        "keywords": [
            "backlink management tool",
            "backlink system",
            "linkody alternative"
        ]
    }

    Body (CSV upload — multipart/form-data):
        domain_id, platform, region, isocode, language_code  (form fields)
        file: CSV with a "keyword" column (or single-column, no header)

    Returns: { created_count, skipped_count, seo_created_count, seo_skipped_count, details }
    """
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only admins can import keywords'}, status=status.HTTP_403_FORBIDDEN)

    domain_id = request.data.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        domain = Domain.objects.get(pk=domain_id, organisation=request.user.organisation)
    except Domain.DoesNotExist:
        return Response({'error': 'Domain not found or not in your organization'}, status=status.HTTP_404_NOT_FOUND)

    # ---- Collect keyword strings ----
    keyword_strings = []

    # Source 1: JSON list
    json_keywords = request.data.get('keywords', [])
    if isinstance(json_keywords, list):
        keyword_strings.extend([str(k).strip().lower() for k in json_keywords if str(k).strip()])

    # Source 2: CSV file upload
    csv_file = request.FILES.get('file')
    if csv_file:
        import csv, io
        try:
            decoded = csv_file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))
            fieldnames = [f.lower().strip() for f in (reader.fieldnames or [])]

            if 'keyword' in fieldnames:
                for row in reader:
                    kw = (row.get('keyword') or row.get('Keyword') or '').strip().lower()
                    if kw:
                        keyword_strings.append(kw)
            else:
                # Single-column CSV or no header — treat every non-empty line as a keyword
                csv_file.seek(0)
                decoded = csv_file.read().decode('utf-8-sig')
                for line in decoded.splitlines():
                    kw = line.strip().strip('"').strip("'").lower()
                    if kw:
                        keyword_strings.append(kw)
        except Exception as e:
            return Response({'error': f'Failed to parse CSV file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    # Deduplicate while preserving order
    seen = set()
    unique_keywords = []
    for kw in keyword_strings:
        if kw not in seen and len(kw) <= 255:
            seen.add(kw)
            unique_keywords.append(kw)

    if not unique_keywords:
        return Response({'error': 'No valid keywords provided'}, status=status.HTTP_400_BAD_REQUEST)

    # ---- Check keyword quota ----
    org = request.user.organisation
    kw_limit = org.seo_keyword_limit if org else 3000
    current_count = SeoKeywordRank.objects.filter(domain__organisation=org).count()
    remaining = max(0, kw_limit - current_count)
    if len(unique_keywords) > remaining:
        return Response({
            'error': f'Keyword limit exceeded. You can add {remaining} more keyword(s) (limit: {kw_limit}, used: {current_count}).',
            'remaining': remaining,
            'limit': kw_limit,
            'used': current_count,
        }, status=status.HTTP_400_BAD_REQUEST)

    # ---- Shared SEO config ----
    platform = request.data.get('platform', 'desktop')
    if platform not in ('desktop', 'mobile'):
        platform = 'desktop'
    region = request.data.get('region', 'google.com')
    isocode = request.data.get('isocode', 'us')
    language_code = request.data.get('language_code', 'en')
    geo_target = request.data.get('geo_target', '')
    geo_target_uule = request.data.get('geo_target_uule', '')
    target_url = request.data.get('target_url', '')

    # Tags support — accept JSON string (from FormData) or list (from JSON body)
    import json as _json
    raw_tags = request.data.get('tags', [])
    if isinstance(raw_tags, str):
        try:
            raw_tags = _json.loads(raw_tags)
        except (ValueError, TypeError):
            raw_tags = []
    tags = list(set(t.strip().lower() for t in raw_tags if isinstance(t, str) and t.strip()))[:20]

    # ---- Step 1: Bulk get-or-create in Keyword table ----
    from keywords.models import Keyword as KwModel

    kw_created = 0
    kw_skipped = 0
    seo_created = 0
    seo_skipped = 0
    details = []

    with transaction.atomic():
        for kw_text in unique_keywords:
            kw_obj, was_new = KwModel.objects.get_or_create(
                keyword=kw_text,
                domain=domain,
                defaults={
                    'source': 'manual',
                    'auto_generate_prompts': False,
                }
            )
            if was_new:
                kw_created += 1
            else:
                kw_skipped += 1

            # ---- Step 2: Create SeoKeywordRank entry ----
            defaults = {
                'region': region,
                'isocode': isocode,
                'language_code': language_code,
                'geo_target': geo_target,
                'geo_target_uule': geo_target_uule,
                'auto_call_status': 'avail',
            }
            if target_url:
                defaults['target_url'] = target_url
            if tags:
                defaults['tags'] = tags

            seo_obj, seo_was_new = SeoKeywordRank.objects.get_or_create(
                keyword=kw_obj,
                domain=domain,
                platform=platform,
                defaults=defaults,
            )
            if seo_was_new:
                seo_created += 1
                details.append({'keyword': kw_text, 'status': 'created'})
            else:
                seo_skipped += 1
                details.append({'keyword': kw_text, 'status': 'already_tracked'})

    return Response({
        'success': True,
        'keyword_created_count': kw_created,
        'keyword_skipped_count': kw_skipped,
        'seo_created_count': seo_created,
        'seo_skipped_count': seo_skipped,
        'total_processed': len(unique_keywords),
        'details': details[:50],
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
        try:
            snippets = kw.snippets_details or {}
            if kw.ads and isinstance(snippets, dict) and 'ads' in snippets:
                ads_data = snippets['ads']
                # SERP API returns ads as a list; convert to counts
                if isinstance(ads_data, list):
                    top_count = len(ads_data)
                    bottom_count = 0
                    ads_status = 'no'
                elif isinstance(ads_data, dict):
                    top_count = int(ads_data.get('top_count', 0) or 0)
                    bottom_count = int(ads_data.get('bottom_count', 0) or 0)
                    ads_status = ads_data.get('status', 'no')
                else:
                    top_count = 0
                    bottom_count = 0
                    ads_status = 'no'

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
        except (TypeError, ValueError, AttributeError):
            pass

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

    # 'done' = scraped successfully, 'fail' = SERP API rejected/empty (e.g.
    # DataBlue success=false, ScrapingDog 4xx). Both terminate the keyword for
    # this run, so they together gate "is the run finished?", but we need them
    # separately to distinguish a real success from a SERP-service outage.
    succeeded_count = SeoKeywordRank.objects.filter(
        domain_id=domain_id,
        auto_call_status='done',
    ).count()
    failed_count = SeoKeywordRank.objects.filter(
        domain_id=domain_id,
        auto_call_status='fail',
    ).count()
    done_count = succeeded_count + failed_count
    # Actively processing keywords
    running_count = SeoKeywordRank.objects.filter(
        domain_id=domain_id,
        auto_call_status__in=['busy', 'load', 'read'],
    ).count()
    # Keywords waiting to be picked up by the next batch
    pending_count = SeoKeywordRank.objects.filter(
        domain_id=domain_id,
        auto_call_status='avail',
    ).count()

    # refreshing while anything is running OR still pending — covers the
    # inter-batch gap (process_seo_domain_task auto-schedules a follow-up
    # batch with a 10s countdown when 'avail' keywords remain). The frontend
    # has its own 30s no-progress stale-detection for genuinely stuck cases,
    # so a generous 'is_refreshing' here doesn't risk an infinite spinner.
    is_refreshing = running_count > 0 or pending_count > 0
    progress = int((done_count / total) * 100) if total > 0 else 0

    # Error surface: refresh has finished but every attempted keyword failed.
    # This is the "SERP service is rejecting our requests" state (invalid key,
    # account out of credits, provider down). Without this, the frontend sees
    # status='done' and shows 100% completion even though no rank values were
    # actually written.
    error_message = None
    if not is_refreshing and failed_count > 0 and succeeded_count == 0:
        error_message = "SERP service is currently unavailable. Please try again after some time."
        current_status = 'error'
    elif is_refreshing:
        current_status = 'running'
    else:
        current_status = 'done'

    return Response({
        'refreshing': is_refreshing,
        'total': total,
        'completed': done_count,
        'succeeded': succeeded_count,
        'failed': failed_count,
        'running': running_count,
        'pending': pending_count,
        'progress': progress,
        'status': current_status,
        'error': error_message,
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

        retry_only = str(request.data.get('retry_only', '')).lower() in ('true', '1', 'yes')

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

        if retry_only:
            # Only process keywords still in 'avail' (stuck/unprocessed).
            # Reset 'fail' back to 'avail' so they get a fresh attempt.
            fail_reset = SeoKeywordRank.objects.filter(
                domain_id=domain_id,
                auto_call_status='fail',
            ).update(auto_call_status='avail')
            remaining = SeoKeywordRank.objects.filter(
                domain_id=domain_id,
                auto_call_status='avail',
            ).count()
            logger.info(f"Retry-only mode: {remaining} keywords pending ({fail_reset} reset from fail) for domain {domain_id}")
        else:
            # Reset ALL keyword statuses to avail — full refresh
            SeoKeywordRank.objects.filter(
                domain_id=domain_id,
            ).exclude(
                auto_call_status='avail',
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
            if retry_only:
                msg = f'Retrying {remaining} remaining keywords'
            elif seeded_count:
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
      3. Fresh DataBlue call (top results only)
    Updates SeoCompetitorAnalysis to COMP or FAIL.
    """
    from urllib.parse import urlparse
    from django.db import connection
    from seo_rankings.services import datablue_service

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
        datablue_key = getattr(settings, 'DATABLUE_API_KEY', '') or ''

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

            # --- Source 3: Fresh DataBlue call ---
            if not competitors and datablue_key:
                kw_text = kw.keyword.keyword if kw.keyword else ''
                if kw_text:
                    page_json = datablue_service.fetch_one(
                        keyword_text=kw_text,
                        isocode=kw.isocode or 'us',
                        language_code=kw.language_code or 'en',
                    )
                    fresh_calls += 1

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


# ---------------------------------------------------------------------------
# SEO Report Sheets CRUD
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_report_sheet_list(request):
    """List all report sheets for a domain."""
    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id required'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_ids = list(_get_user_domain_ids(request.user))
    if int(domain_id) not in allowed_ids:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    sheets = SeoReportSheet.objects.filter(
        domain_id=domain_id, is_active=True
    ).order_by('-created_at')

    data = []
    for s in sheets:
        data.append({
            'id': s.id,
            'sheet_name': s.sheet_name,
            'category': s.category,
            'sheet_type': s.sheet_type,
            'metrics': s.metrics,
            'change_units': s.change_units,
            'schedule': s.schedule,
            'duration': s.duration,
            'order_by': s.order_by,
            'created_at': s.created_at.isoformat(),
        })

    return Response({'sheets': data, 'count': len(data)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seo_report_sheet_add(request):
    """Add a new report sheet."""
    domain_id = request.data.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id required'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_ids = list(_get_user_domain_ids(request.user))
    if int(domain_id) not in allowed_ids:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    sheet_name = request.data.get('sheet_name', '').strip()
    category = request.data.get('category', 'gsc')
    sheet_type = request.data.get('sheet_type', '')
    metrics = request.data.get('metrics', [])
    change_units = request.data.get('change_units', [])
    schedule = request.data.get('schedule', 'weekly')
    duration = request.data.get('duration', 2)
    order_by = request.data.get('order_by', 'Ascending')

    if not sheet_name:
        return Response({'error': 'sheet_name is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not sheet_type:
        return Response({'error': 'sheet_type is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Validate GSC/GA connection before allowing sheet creation
    from integrations.models import Integration

    gsc_types = ('gsc_pages', 'gsc_branded_queries', 'gsc_non_branded_queries', 'gsc_queries', 'gsc_overview')
    ga_types = ('ga_landing_pages', 'ga_other_sources', 'ga_overview', 'ga_organic_traffic_breakup')

    if sheet_type in gsc_types:
        gsc_integration = Integration.objects.filter(
            domain_id=domain_id, type='search_console', status='active'
        ).exclude(provider_id='').exclude(provider_id='pending_selection').exclude(provider_id__isnull=True).first()
        if not gsc_integration:
            return Response(
                {'error': 'Connect Google Search Console to add GSC sheet.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Verify actual API access before creating the sheet
        gsc_check = _verify_gsc_access(gsc_integration)
        if gsc_check:
            return Response({'error': gsc_check}, status=status.HTTP_400_BAD_REQUEST)

    if sheet_type in ga_types:
        ga_integration = Integration.objects.filter(
            domain_id=domain_id, type='google_analytics', status='active'
        ).exclude(provider_id='').exclude(provider_id='pending_selection').exclude(provider_id__isnull=True).first()
        if not ga_integration:
            return Response(
                {'error': 'Connect Google Analytics to add GA sheet.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Verify actual API access before creating the sheet
        ga_check = _verify_ga_access(ga_integration)
        if ga_check:
            return Response({'error': ga_check}, status=status.HTTP_400_BAD_REQUEST)

    sheet = SeoReportSheet.objects.create(
        domain_id=domain_id,
        created_by=request.user,
        sheet_name=sheet_name,
        category=category,
        sheet_type=sheet_type,
        metrics=metrics,
        change_units=change_units,
        schedule=schedule,
        duration=duration,
        order_by=order_by,
    )

    return Response({
        'id': sheet.id,
        'message': f'Report sheet "{sheet_name}" added successfully.',
    }, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def seo_report_sheet_delete(request, pk):
    """Soft-delete a report sheet."""
    allowed_ids = list(_get_user_domain_ids(request.user))
    try:
        sheet = SeoReportSheet.objects.get(id=pk, is_active=True)
    except SeoReportSheet.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if sheet.domain_id not in allowed_ids:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    sheet.is_active = False
    sheet.save(update_fields=['is_active', 'modified_at'])

    return Response({'message': 'Report sheet deleted successfully.'})


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def seo_report_sheet_update(request, pk):
    """Update a report sheet."""
    allowed_ids = list(_get_user_domain_ids(request.user))
    try:
        sheet = SeoReportSheet.objects.get(id=pk, is_active=True)
    except SeoReportSheet.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if sheet.domain_id not in allowed_ids:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    update_fields = ['modified_at']
    for field in ['sheet_name', 'category', 'sheet_type', 'metrics', 'change_units', 'schedule', 'duration', 'order_by']:
        if field in request.data:
            setattr(sheet, field, request.data[field])
            update_fields.append(field)

    sheet.save(update_fields=update_fields)

    return Response({
        'id': sheet.id,
        'message': 'Report sheet updated successfully.',
    })


# ---------------------------------------------------------------------------
# Report Sheet Data — Fetch live GSC/GA data for configured sheets
# ---------------------------------------------------------------------------


def _verify_gsc_access(integration):
    """
    Test GSC API access for the integration. Returns error string if failed, None if OK.
    """
    try:
        from integrations.google_oauth import get_credentials_from_integration
        from googleapiclient.discovery import build

        credentials = get_credentials_from_integration(integration)
        if not credentials:
            return 'Google Search Console credentials are invalid or expired. Please reconnect GSC.'

        service = build('searchconsole', 'v1', credentials=credentials)
        site_url = integration.provider_id

        # Make a minimal test query to verify access
        service.searchanalytics().query(
            siteUrl=site_url,
            body={
                'startDate': (date.today() - timedelta(days=7)).isoformat(),
                'endDate': (date.today() - timedelta(days=3)).isoformat(),
                'dimensions': ['page'],
                'rowLimit': 1,
            }
        ).execute()
        return None  # Access OK
    except Exception as e:
        err = str(e)
        if 'permission' in err.lower() or '403' in err:
            return 'Insufficient permissions for this GSC property. Please verify that the connected Google account has access to this site in Google Search Console.'
        if 'not found' in err.lower() or '404' in err:
            return 'The GSC site property was not found. Please reconnect Google Search Console.'
        if 'invalid' in err.lower() or 'expired' in err.lower() or '401' in err:
            return 'Google Search Console credentials have expired. Please reconnect GSC in Domain Settings.'
        logger.error(f"GSC access verification failed: {e}")
        return 'Unable to access Google Search Console. Please reconnect GSC in Domain Settings.'


def _verify_ga_access(integration):
    """
    Test GA4 API access for the integration. Returns error string if failed, None if OK.
    """
    try:
        from integrations.google_oauth import get_credentials_from_integration
        from googleapiclient.discovery import build

        credentials = get_credentials_from_integration(integration)
        if not credentials:
            return 'Google Analytics credentials are invalid or expired. Please reconnect GA.'

        service = build('analyticsdata', 'v1beta', credentials=credentials)
        property_id = integration.provider_id

        # Make a minimal test query to verify access
        service.properties().runReport(
            property=property_id,
            body={
                'dateRanges': [{'startDate': (date.today() - timedelta(days=7)).isoformat(), 'endDate': (date.today() - timedelta(days=1)).isoformat()}],
                'dimensions': [{'name': 'date'}],
                'metrics': [{'name': 'sessions'}],
                'limit': 1,
            }
        ).execute()
        return None  # Access OK
    except Exception as e:
        err = str(e)
        if 'permission' in err.lower() or '403' in err:
            return 'Insufficient permissions for this GA4 property. Please verify that the connected Google account has access to this property in Google Analytics.'
        if 'not found' in err.lower() or '404' in err:
            return 'The GA4 property was not found. Please reconnect Google Analytics.'
        if 'invalid' in err.lower() or 'expired' in err.lower() or '401' in err:
            return 'Google Analytics credentials have expired. Please reconnect GA in Domain Settings.'
        logger.error(f"GA access verification failed: {e}")
        return 'Unable to access Google Analytics. Please reconnect GA in Domain Settings.'


def _get_date_ranges(schedule, duration, order_asc=True, data_lag_days=3):
    """
    Calculate date ranges based on schedule (weekly/monthly) and duration.
    Returns list of (start_date, end_date, label) tuples.
    data_lag_days defaults to 3 (GSC reporting lag); pass 1 for GA which
    has fresh data through yesterday.
    """
    today = date.today() - timedelta(days=data_lag_days)
    ranges = []

    if schedule == 'weekly':
        # Find last Sunday as week end
        days_since_sunday = (today.weekday() + 1) % 7
        last_sunday = today - timedelta(days=days_since_sunday)

        for i in range(duration):
            end = last_sunday - timedelta(weeks=i)
            start = end - timedelta(days=6)
            label = f"{start.strftime('%d %b')}-{end.strftime('%d %b')}"
            ranges.append((start, end, label))
    else:  # monthly
        for i in range(duration):
            # Go back i months
            month = today.month - i
            year = today.year
            while month <= 0:
                month += 12
                year -= 1
            # First and last day of that month
            import calendar
            _, last_day = calendar.monthrange(year, month)
            start = date(year, month, 1)
            end = date(year, month, last_day)
            if end > today:
                end = today
            label = start.strftime('%b %Y')
            ranges.append((start, end, label))

    if order_asc:
        ranges.reverse()
    return ranges


def _fetch_gsc_report_data(integration, sheet):
    """
    Fetch GSC data for a report sheet configuration.

    Shows N period columns based on sheet.duration. For monthly schedule, the
    current incomplete month is prorated — cell shows "raw (prorated)" and the
    column label gets a "(PR)" suffix. Weekly does not prorate (per product
    spec — show actual values only). Monthly always appends MOM % and YOY %;
    weekly always appends WOW %. Rate metrics (CTR, position) are never
    prorated.
    """
    import calendar as _cal
    from datetime import date as _date
    from integrations.utils.prorate import calculate_prorate_factor
    from integrations.google_oauth import get_credentials_from_integration
    from googleapiclient.discovery import build

    credentials = get_credentials_from_integration(integration)
    if not credentials:
        return {'columns': [], 'rows': [], 'error': 'Invalid credentials'}

    service  = build('searchconsole', 'v1', credentials=credentials)
    site_url = integration.provider_id

    order_asc   = sheet.order_by == 'Ascending'
    date_ranges = _get_date_ranges(sheet.schedule, sheet.duration, order_asc)

    metrics_list = sheet.metrics or ['clicks', 'impressions', 'ctr', 'position']

    ml_map   = {'clicks': 'Clicks', 'impressions': 'Impressions', 'ctr': 'CTR', 'position': 'Avg Position'}
    rate_map = {'clicks': False,    'impressions': False,         'ctr': True,  'position': True}

    if sheet.sheet_type in ('gsc_pages',):
        dimension = 'page'
        dim_label = 'Pages'
    elif sheet.sheet_type in ('gsc_branded_queries', 'gsc_non_branded_queries', 'gsc_queries'):
        dimension = 'query'
        dim_label = 'Queries'
    else:
        dimension = 'page'
        dim_label = 'Pages'

    domain_name = (site_url
                   .replace('sc-domain:', '')
                   .replace('https://', '')
                   .replace('http://', '')
                   .split('/')[0].split('.')[0])

    def _dim_filters():
        if sheet.sheet_type == 'gsc_branded_queries':
            return [{'dimension': 'query', 'operator': 'contains', 'expression': domain_name}]
        if sheet.sheet_type == 'gsc_non_branded_queries':
            return [{'dimension': 'query', 'operator': 'excludingRegex', 'expression': f'(?i){domain_name}'}]
        return None
    dim_filters = _dim_filters()

    # ── Prorate setup: only the current calendar month (monthly schedule) ────
    is_monthly = sheet.schedule == 'monthly'
    is_weekly  = sheet.schedule == 'weekly'
    today      = _date.today()
    cur_label  = None
    factor     = 1.0
    days_elapsed = total_days = None
    if is_monthly:
        for s_dt, _e_dt, lbl in date_ranges:
            if s_dt.year == today.year and s_dt.month == today.month:
                _, last_day  = _cal.monthrange(s_dt.year, s_dt.month)
                cur_full_end = _date(s_dt.year, s_dt.month, last_day)
                days_elapsed, total_days, factor = calculate_prorate_factor(s_dt, cur_full_end, data_lag_days=3)
                if factor != 1.0:
                    cur_label = lbl
                break
    is_prorated = factor != 1.0

    # ── Fetch each period ───────────────────────────────────────────────────
    all_keys   = set()
    range_data = {}
    api_errors = []
    for start_dt, end_dt, label in date_ranges:
        body = {
            'startDate':  start_dt.isoformat(),
            'endDate':    end_dt.isoformat(),
            'dimensions': [dimension],
            'rowLimit':   500,
        }
        if dim_filters:
            body['dimensionFilterGroups'] = [{'filters': dim_filters}]
        try:
            response = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
            data_map = {}
            for row in response.get('rows', []):
                key = row.get('keys', [''])[0]
                all_keys.add(key)
                data_map[key] = {
                    'clicks':      row.get('clicks', 0),
                    'impressions': row.get('impressions', 0),
                    'ctr':         round(row.get('ctr', 0) * 100, 2),
                    'position':    round(row.get('position', 0), 1),
                }
            range_data[label] = data_map
        except Exception as e:
            logger.error(f"GSC API error ({label}) for sheet {sheet.id}: {e}")
            range_data[label] = {}
            api_errors.append(str(e))

    # ── YOY fetch (monthly only) — same calendar month one year prior to the
    #    rightmost (last) period in the result table ───────────────────────
    yoy_data = {}   # {dim_key: {metric: value}}
    if is_monthly and date_ranges:
        cur_s, cur_e, _ = date_ranges[-1]
        yoy_s = _date(cur_s.year - 1, cur_s.month, cur_s.day)
        yoy_e = _date(cur_e.year - 1, cur_e.month, cur_e.day)
        body = {
            'startDate':  yoy_s.isoformat(),
            'endDate':    yoy_e.isoformat(),
            'dimensions': [dimension],
            'rowLimit':   500,
        }
        if dim_filters:
            body['dimensionFilterGroups'] = [{'filters': dim_filters}]
        try:
            resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
            for row in resp.get('rows', []):
                key = row.get('keys', [''])[0]
                yoy_data[key] = {
                    'clicks':      row.get('clicks', 0),
                    'impressions': row.get('impressions', 0),
                    'ctr':         round(row.get('ctr', 0) * 100, 2),
                    'position':    round(row.get('position', 0), 1),
                }
        except Exception as e:
            logger.error(f"GSC YOY API error for sheet {sheet.id}: {e}")

    if not all_keys and len(api_errors) == len(date_ranges) and api_errors:
        return {'columns': [], 'rows': [], 'total_rows': 0, 'error': f'GSC API error: {api_errors[0]}'}

    # ── Columns ─────────────────────────────────────────────────────────────
    range_labels         = [r[2] for r in date_ranges]
    range_labels_display = [(f"{lbl} (PR)" if lbl == cur_label else lbl) for lbl in range_labels]

    if is_monthly:
        extra_pct_cols = ['MOM %', 'YOY %']
    elif is_weekly:
        extra_pct_cols = ['WOW %']
    else:
        extra_pct_cols = []

    def _pct_pretty(cur_v, base_v):
        if base_v and base_v != 0:
            return f"{round((cur_v - base_v) / base_v * 100, 1):+.1f}%"
        return 'N/A'

    columns = ['Sr No', dim_label]
    for metric in metrics_list:
        ml      = ml_map.get(metric, metric.capitalize())
        is_rate = rate_map.get(metric, False)
        for rl_orig, rl_disp in zip(range_labels, range_labels_display):
            label_to_use = rl_orig if is_rate else rl_disp
            columns.append(f"{label_to_use} {ml}")
        for pc in extra_pct_cols:
            columns.append(f"{ml} {pc}")

    # ── Rows ────────────────────────────────────────────────────────────────
    sorted_keys = sorted(all_keys)
    rows = []
    for idx, key in enumerate(sorted_keys, 1):
        row = {'Sr No': idx, dim_label: key}
        for metric in metrics_list:
            ml      = ml_map.get(metric, metric.capitalize())
            is_rate = rate_map.get(metric, False)
            vals_for_change = []
            for rl_orig, rl_disp in zip(range_labels, range_labels_display):
                raw = range_data.get(rl_orig, {}).get(key, {}).get(metric, 0)
                if is_prorated and rl_orig == cur_label and not is_rate:
                    proj      = round(raw * factor)
                    cell      = f"{raw} ({proj})"
                    cmp_value = proj
                else:
                    cell      = raw
                    cmp_value = raw
                label_to_use = rl_orig if is_rate else rl_disp
                row[f"{label_to_use} {ml}"] = cell
                vals_for_change.append(cmp_value)

            cur_v = vals_for_change[-1] if vals_for_change else 0
            prv_v = vals_for_change[-2] if len(vals_for_change) >= 2 else None
            if is_monthly:
                row[f"{ml} MOM %"] = _pct_pretty(cur_v, prv_v) if prv_v is not None else 'N/A'
                yoy_v = yoy_data.get(key, {}).get(metric, 0)
                row[f"{ml} YOY %"] = _pct_pretty(cur_v, yoy_v)
            elif is_weekly:
                row[f"{ml} WOW %"] = _pct_pretty(cur_v, prv_v) if prv_v is not None else 'N/A'
        rows.append(row)

    return {
        'columns':         columns,
        'rows':            rows,
        'total_rows':      len(rows),
        'metrics_headers': [ml_map.get(m, m.capitalize()) for m in metrics_list],
        'is_prorated':     is_prorated,
        'days_elapsed':    days_elapsed,
        'total_days':      total_days,
    }


def _fetch_ga_report_data(integration, sheet):
    """
    Fetch GA data for a report sheet configuration.

    Shows N period columns based on sheet.duration (matches Rankmaxx layout).
    For monthly: applies prorate to the current incomplete month — cell shows
    "raw (prorated)" and the column label is suffixed with "(PR)". Always
    appends MOM % and YOY % comparison columns (YOY uses an extra API call
    against the same calendar month one year prior to the rightmost period).
    For weekly: no prorate (per product spec). Appends a WOW % column.
    Always appends GA4 Leads metrics (Organic / Direct / Total) per period.
    """
    import calendar as _cal
    from datetime import date as _date
    from integrations.utils.prorate import calculate_prorate_factor
    from integrations.google_oauth import get_credentials_from_integration
    from googleapiclient.discovery import build

    order_asc   = sheet.order_by == 'Ascending'
    date_ranges = _get_date_ranges(sheet.schedule, sheet.duration, order_asc, data_lag_days=1)

    credentials = get_credentials_from_integration(integration)
    if not credentials:
        return {'columns': [], 'rows': [], 'error': 'Invalid credentials'}

    service = build('analyticsdata', 'v1beta', credentials=credentials)
    property_id = integration.provider_id

    if sheet.sheet_type == 'ga_landing_pages':
        ga_dimension   = 'landingPagePlusQueryString'
        dim_label      = 'Landing Pages'
        ga_metrics     = ['sessions', 'totalUsers', 'screenPageViews', 'bounceRate']
        metric_labels  = ['Sessions', 'Users', 'Page Views', 'Bounce Rate']
        metric_is_rate = [False, False, False, True]
    else:
        ga_dimension   = 'sessionDefaultChannelGroup'
        dim_label      = 'Source'
        ga_metrics     = ['sessions', 'totalUsers']
        metric_labels  = ['Sessions', 'Users']
        metric_is_rate = [False, False]

    # ── Prorate setup: only the current calendar month (monthly schedule) ────
    is_monthly = sheet.schedule == 'monthly'
    is_weekly  = sheet.schedule == 'weekly'
    today      = _date.today()
    cur_label  = None      # range label of the period that should show (PR)
    factor     = 1.0
    days_elapsed = total_days = None
    if is_monthly:
        for s_dt, _e_dt, lbl in date_ranges:
            if s_dt.year == today.year and s_dt.month == today.month:
                _, last_day  = _cal.monthrange(s_dt.year, s_dt.month)
                cur_full_end = _date(s_dt.year, s_dt.month, last_day)
                days_elapsed, total_days, factor = calculate_prorate_factor(s_dt, cur_full_end, data_lag_days=1)
                if factor != 1.0:
                    cur_label = lbl
                break
    is_prorated = factor != 1.0

    # Landing-page sheet is scoped to Organic Search channel only; other GA
    # sheet types remain unfiltered.
    landing_page_channel_filter = None
    if sheet.sheet_type == 'ga_landing_pages':
        landing_page_channel_filter = {
            'filter': {
                'fieldName': 'sessionDefaultChannelGroup',
                'stringFilter': {'value': 'Organic Search', 'matchType': 'EXACT'},
            }
        }

    # ── Fetch primary metrics per period ────────────────────────────────────
    all_keys   = set()
    range_data = {}
    api_errors = []
    for start_dt, end_dt, label in date_ranges:
        try:
            body = {
                'dateRanges': [{'startDate': start_dt.isoformat(), 'endDate': end_dt.isoformat()}],
                'dimensions': [{'name': ga_dimension}],
                'metrics': [{'name': m} for m in ga_metrics],
                'limit': 500,
            }
            if landing_page_channel_filter:
                body['dimensionFilter'] = landing_page_channel_filter
            response = service.properties().runReport(property=property_id, body=body).execute()
            data_map = {}
            for row in response.get('rows', []):
                key = row['dimensionValues'][0]['value']
                all_keys.add(key)
                vals = {}
                for i, ml in enumerate(metric_labels):
                    raw = row['metricValues'][i]['value']
                    vals[ml] = round(float(raw), 2) if '.' in raw else int(raw)
                data_map[key] = vals
            range_data[label] = data_map
        except Exception as e:
            logger.error(f"GA API error ({label}) for sheet {sheet.id}: {e}")
            range_data[label] = {}
            api_errors.append(str(e))

    # ── Fetch GA4 Leads per period (filtered by all_leads_event_action) ─────
    KEY_EVENT_NAME = 'all_leads_event_action'
    leads_data = {}   # {label: {channel: count}}
    for start_dt, end_dt, label in date_ranges:
        try:
            body = {
                'dateRanges': [{'startDate': start_dt.isoformat(), 'endDate': end_dt.isoformat()}],
                'dimensions': [{'name': 'sessionDefaultChannelGroup'}],
                'metrics':    [{'name': 'keyEvents'}],
                'dimensionFilter': {
                    'filter': {
                        'fieldName': 'eventName',
                        'stringFilter': {'value': KEY_EVENT_NAME, 'matchType': 'EXACT'}
                    }
                },
                'limit': 500,
            }
            response = service.properties().runReport(property=property_id, body=body).execute()
            ch_map = {}
            for row in response.get('rows', []):
                ch_map[row['dimensionValues'][0]['value']] = int(row['metricValues'][0]['value'])
            leads_data[label] = ch_map
        except Exception as e:
            logger.error(f"GA Leads API error ({label}) for sheet {sheet.id}: {e}")
            leads_data[label] = {}

    # ── YOY fetch (monthly only) — same calendar month one year prior to the
    #    rightmost (last) period in the result table ───────────────────────
    yoy_primary  = {}   # {dim_key: {ml: value}}
    yoy_leads_ch = {}   # {channel: count}
    if is_monthly and date_ranges:
        cur_s, cur_e, _ = date_ranges[-1]
        yoy_s = _date(cur_s.year - 1, cur_s.month, cur_s.day)
        yoy_e = _date(cur_e.year - 1, cur_e.month, cur_e.day)
        try:
            body = {
                'dateRanges': [{'startDate': yoy_s.isoformat(), 'endDate': yoy_e.isoformat()}],
                'dimensions': [{'name': ga_dimension}],
                'metrics': [{'name': m} for m in ga_metrics],
                'limit': 500,
            }
            if landing_page_channel_filter:
                body['dimensionFilter'] = landing_page_channel_filter
            resp = service.properties().runReport(property=property_id, body=body).execute()
            for row in resp.get('rows', []):
                key = row['dimensionValues'][0]['value']
                vals = {}
                for i, ml in enumerate(metric_labels):
                    raw = row['metricValues'][i]['value']
                    vals[ml] = round(float(raw), 2) if '.' in raw else int(raw)
                yoy_primary[key] = vals
        except Exception as e:
            logger.error(f"GA YOY API error for sheet {sheet.id}: {e}")
        try:
            body = {
                'dateRanges': [{'startDate': yoy_s.isoformat(), 'endDate': yoy_e.isoformat()}],
                'dimensions': [{'name': 'sessionDefaultChannelGroup'}],
                'metrics':    [{'name': 'keyEvents'}],
                'dimensionFilter': {
                    'filter': {
                        'fieldName': 'eventName',
                        'stringFilter': {'value': KEY_EVENT_NAME, 'matchType': 'EXACT'}
                    }
                },
                'limit': 500,
            }
            resp = service.properties().runReport(property=property_id, body=body).execute()
            for row in resp.get('rows', []):
                yoy_leads_ch[row['dimensionValues'][0]['value']] = int(row['metricValues'][0]['value'])
        except Exception as e:
            logger.error(f"GA Leads YOY API error for sheet {sheet.id}: {e}")

    if not all_keys and len(api_errors) == len(date_ranges) and api_errors:
        return {'columns': [], 'rows': [], 'total_rows': 0, 'error': f'GA API error: {api_errors[0]}'}

    # ── Column headers (last incomplete month label gets "(PR)") ────────────
    range_labels         = [r[2] for r in date_ranges]
    range_labels_display = [(f"{lbl} (PR)" if lbl == cur_label else lbl) for lbl in range_labels]

    lead_metric_labels = ['GA4 Organic Leads', 'GA4 Direct Leads', 'Total GA4 Leads']
    all_metric_labels  = metric_labels + lead_metric_labels
    all_metric_is_rate = metric_is_rate + [False, False, False]

    # MOM/YOY (monthly) and WOW (weekly) comparison columns are always shown
    if is_monthly:
        extra_pct_cols = ['MOM %', 'YOY %']
    elif is_weekly:
        extra_pct_cols = ['WOW %']
    else:
        extra_pct_cols = []

    def _label_for(rl_orig, rl_disp, ml, is_rate):
        # Rate metrics aren't prorated → no (PR) suffix.
        # Total GA4 Leads is the sum of already-prorated org/drc → no (PR) suffix.
        if is_rate or ml == 'Total GA4 Leads':
            return rl_orig
        return rl_disp

    def _pct_pretty(cur_v, base_v):
        if base_v and base_v != 0:
            return f"{round((cur_v - base_v) / base_v * 100, 1):+.1f}%"
        return 'N/A'

    columns = ['Sr No', dim_label]
    for ml, is_rate in zip(all_metric_labels, all_metric_is_rate):
        for rl_orig, rl_disp in zip(range_labels, range_labels_display):
            columns.append(f"{_label_for(rl_orig, rl_disp, ml, is_rate)} {ml}")
        for pc in extra_pct_cols:
            columns.append(f"{ml} {pc}")

    # ── Rows ────────────────────────────────────────────────────────────────
    def _emit_pct_cols(row, ml, vals_for_change, yoy_value):
        cur_v = vals_for_change[-1] if vals_for_change else 0
        prv_v = vals_for_change[-2] if len(vals_for_change) >= 2 else None
        if is_monthly:
            row[f"{ml} MOM %"] = _pct_pretty(cur_v, prv_v) if prv_v is not None else 'N/A'
            row[f"{ml} YOY %"] = _pct_pretty(cur_v, yoy_value) if yoy_value is not None else 'N/A'
        elif is_weekly:
            row[f"{ml} WOW %"] = _pct_pretty(cur_v, prv_v) if prv_v is not None else 'N/A'

    sorted_keys = sorted(all_keys)
    rows = []
    for idx, key in enumerate(sorted_keys, 1):
        row = {'Sr No': idx, dim_label: key}

        # Primary metrics
        for ml, is_rate in zip(metric_labels, metric_is_rate):
            vals_for_change = []
            for rl_orig, rl_disp in zip(range_labels, range_labels_display):
                raw = range_data.get(rl_orig, {}).get(key, {}).get(ml, 0)
                if is_prorated and rl_orig == cur_label and not is_rate:
                    proj      = round(raw * factor)
                    cell      = f"{raw} ({proj})"
                    cmp_value = proj
                else:
                    cell      = raw
                    cmp_value = raw
                row[f"{_label_for(rl_orig, rl_disp, ml, is_rate)} {ml}"] = cell
                vals_for_change.append(cmp_value)
            yoy_v = yoy_primary.get(key, {}).get(ml, 0) if is_monthly else None
            _emit_pct_cols(row, ml, vals_for_change, yoy_v)

        # GA4 Leads metrics — values are global per period (not per dimension key)
        yoy_org = yoy_leads_ch.get('Organic Search', 0)
        yoy_drc = yoy_leads_ch.get('Direct', 0)
        for ml in lead_metric_labels:
            vals_for_change = []
            for rl_orig, rl_disp in zip(range_labels, range_labels_display):
                ch  = leads_data.get(rl_orig, {})
                org = ch.get('Organic Search', 0)
                drc = ch.get('Direct', 0)

                if ml == 'GA4 Organic Leads':
                    raw = org
                elif ml == 'GA4 Direct Leads':
                    raw = drc
                else:
                    raw = org + drc

                if is_prorated and rl_orig == cur_label:
                    if ml == 'Total GA4 Leads':
                        proj      = round(org * factor) + round(drc * factor)
                        cell      = proj
                        cmp_value = proj
                    else:
                        proj      = round(raw * factor)
                        cell      = f"{raw} ({proj})"
                        cmp_value = proj
                else:
                    cell      = raw
                    cmp_value = raw
                row[f"{_label_for(rl_orig, rl_disp, ml, False)} {ml}"] = cell
                vals_for_change.append(cmp_value)
            if is_monthly:
                if ml == 'GA4 Organic Leads':
                    yoy_v = yoy_org
                elif ml == 'GA4 Direct Leads':
                    yoy_v = yoy_drc
                else:
                    yoy_v = yoy_org + yoy_drc
            else:
                yoy_v = None
            _emit_pct_cols(row, ml, vals_for_change, yoy_v)

        rows.append(row)

    return {
        'columns':         columns,
        'rows':            rows,
        'total_rows':      len(rows),
        'metrics_headers': all_metric_labels,
        'is_prorated':     is_prorated,
        'days_elapsed':    days_elapsed,
        'total_days':      total_days,
    }


_BRAND_STOPWORDS = {
    'life', 'insurance', 'bank', 'the', 'ltd', 'limited', 'llc', 'inc',
    'co', 'company', 'corp', 'corporation', 'group', 'india', 'online',
    'pvt', 'private', 'gmbh', 'plc', 'sa', 'usa',
}


def _resolve_brand_tokens(integration):
    """
    Pick brand keyword tokens for branded/non-branded GSC splits.
    Order of preference:
      1. Tokens parsed from Domain.name (e.g. "Canara HSBC Life" → ["canara","hsbc"])
      2. URL-derived single token (host first label, e.g. "canarahsbclife")
    Stopwords like "life", "insurance" are dropped so generic suffixes don't
    pollute the regex. Returns a list of unique lowercase tokens.
    """
    import re as _re

    tokens = []
    domain = getattr(integration, 'domain', None)
    domain_name = getattr(domain, 'name', '') if domain else ''
    if domain_name:
        for raw in _re.split(r'[\s/_\-,&]+', domain_name):
            t = _re.sub(r'[^a-z0-9]+', '', raw.lower())
            if len(t) >= 3 and t not in _BRAND_STOPWORDS and t not in tokens:
                tokens.append(t)

    if not tokens:
        site_url = getattr(integration, 'provider_id', '') or ''
        host = (site_url
                .replace('sc-domain:', '')
                .replace('https://', '')
                .replace('http://', '')
                .split('/')[0])
        first = host.split('.')[0] if host else ''
        first = _re.sub(r'[^a-z0-9]+', '', first.lower())
        if first:
            tokens = [first]

    return tokens[:5]


def _fetch_gsc_overview_data(integration, sheet):
    """
    GSC Overview — N-period metric-down view. Columns honour sheet.duration:
      Metric | Period_1 | Period_2 | ... | Period_N | MOM%/WOW% | YOY% (monthly only)
    Rows are expanded into Total / Branded / Non-Branded for Clicks,
    Impressions and CTR, plus a single Avg Position row. Branded values come
    from one extra GSC call per period filtered by brand-keyword regex (tokens
    derived from the domain name). Non-Branded = Total − Branded for counts;
    CTR is derived from clicks÷impressions for branded and non-branded so the
    rate stays internally consistent with the prorated counts.
    Prorate applies only to the current incomplete calendar month (monthly
    schedule). Weekly reports include only complete weeks — no prorate.
    YOY comparison uses the same calendar month one year prior to the last
    period in the result set.
    """
    import calendar as _cal
    from datetime import date as _date
    from integrations.utils.prorate import calculate_prorate_factor
    from integrations.google_oauth import get_credentials_from_integration
    from googleapiclient.discovery import build

    credentials = get_credentials_from_integration(integration)
    if not credentials:
        return {'columns': [], 'rows': [], 'error': 'Invalid credentials'}

    service  = build('searchconsole', 'v1', credentials=credentials)
    site_url = integration.provider_id

    order_asc   = sheet.order_by == 'Ascending'
    date_ranges = _get_date_ranges(sheet.schedule, sheet.duration, order_asc, data_lag_days=3)

    if not date_ranges:
        return {'columns': [], 'rows': [], 'total_rows': 0}

    is_monthly = sheet.schedule == 'monthly'
    is_weekly  = sheet.schedule == 'weekly'

    # ── Prorate setup: current calendar month only (monthly schedule) ────────
    today        = _date.today()
    cur_label    = None
    factor       = 1.0
    days_elapsed = total_days = None
    if is_monthly:
        for s_dt, _e_dt, lbl in date_ranges:
            if s_dt.year == today.year and s_dt.month == today.month:
                _, last_day  = _cal.monthrange(s_dt.year, s_dt.month)
                cur_full_end = _date(s_dt.year, s_dt.month, last_day)
                days_elapsed, total_days, factor = calculate_prorate_factor(
                    s_dt, cur_full_end, data_lag_days=3
                )
                if factor != 1.0:
                    cur_label = lbl
                break
    is_prorated = factor != 1.0

    # ── Brand regex for branded/non-branded split ────────────────────────────
    brand_tokens = _resolve_brand_tokens(integration)
    brand_regex  = f"(?i)({'|'.join(brand_tokens)})" if brand_tokens else None
    branded_filter = (
        [{'dimension': 'query', 'operator': 'includingRegex', 'expression': brand_regex}]
        if brand_regex else None
    )

    def _query_totals(start_dt, end_dt, with_filter=False):
        body = {
            'startDate': start_dt.isoformat(),
            'endDate':   end_dt.isoformat(),
            'rowLimit':  1,
        }
        if with_filter and branded_filter:
            body['dimensionFilterGroups'] = [{'filters': branded_filter}]
        resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
        r_rows = resp.get('rows', [])
        if not r_rows:
            return {'clicks': 0, 'impressions': 0, 'ctr': 0, 'position': 0}
        r = r_rows[0]
        return {
            'clicks':      r.get('clicks', 0),
            'impressions': r.get('impressions', 0),
            'ctr':         round(r.get('ctr', 0) * 100, 2),
            'position':    round(r.get('position', 0), 1),
        }

    # ── Fetch each period's site-wide totals + branded totals ───────────────
    range_total   = {}
    range_branded = {}
    api_errors    = []
    for s_dt, e_dt, label in date_ranges:
        try:
            range_total[label] = _query_totals(s_dt, e_dt, with_filter=False)
        except Exception as e:
            logger.error(f"GSC Overview API error ({label}) for sheet {sheet.id}: {e}")
            range_total[label] = {'clicks': 0, 'impressions': 0, 'ctr': 0, 'position': 0}
            api_errors.append(str(e))

        if branded_filter:
            try:
                range_branded[label] = _query_totals(s_dt, e_dt, with_filter=True)
            except Exception as e:
                logger.error(f"GSC Overview branded API error ({label}) for sheet {sheet.id}: {e}")
                range_branded[label] = {'clicks': 0, 'impressions': 0, 'ctr': 0, 'position': 0}
        else:
            range_branded[label] = {'clicks': 0, 'impressions': 0, 'ctr': 0, 'position': 0}

    # ── YOY fetch — monthly only (totals + branded) ─────────────────────────
    yoy_total = {}
    yoy_branded = {}
    if is_monthly:
        cur_s, cur_e, _ = date_ranges[-1]
        yoy_s = _date(cur_s.year - 1, cur_s.month, 1)
        yoy_e = _date(cur_e.year - 1, cur_e.month, cur_e.day)
        try:
            yoy_total = _query_totals(yoy_s, yoy_e, with_filter=False)
        except Exception as e:
            logger.error(f"GSC Overview YOY API error for sheet {sheet.id}: {e}")
        if branded_filter:
            try:
                yoy_branded = _query_totals(yoy_s, yoy_e, with_filter=True)
            except Exception as e:
                logger.error(f"GSC Overview YOY branded API error for sheet {sheet.id}: {e}")

    if len(api_errors) == len(date_ranges) and api_errors:
        return {'columns': [], 'rows': [], 'total_rows': 0, 'error': f'GSC API error: {api_errors[0]}'}

    # ── Helpers to derive non-branded + branded/non-branded CTR ─────────────
    def _split(period_total, period_branded, key):
        """Return (total, branded, non_branded) for a count metric."""
        t = period_total.get(key, 0) or 0
        b = period_branded.get(key, 0) or 0
        nb = max(t - b, 0)
        return t, b, nb

    def _ctr(clicks, impressions):
        if impressions and impressions > 0:
            return round((clicks / impressions) * 100, 2)
        return 0

    # Build derived per-period values for each metric × bucket combination.
    # bucket ∈ {'total', 'branded', 'non_branded'}
    range_derived = {}   # range_derived[label][metric][bucket] = number
    for s_dt, e_dt, label in date_ranges:
        t = range_total.get(label, {})
        b = range_branded.get(label, {})
        clicks_t,  clicks_b,  clicks_nb  = _split(t, b, 'clicks')
        impr_t,    impr_b,    impr_nb    = _split(t, b, 'impressions')
        range_derived[label] = {
            'clicks': {'total': clicks_t, 'branded': clicks_b, 'non_branded': clicks_nb},
            'impressions': {'total': impr_t, 'branded': impr_b, 'non_branded': impr_nb},
            'ctr': {
                'total':       t.get('ctr', 0) or _ctr(clicks_t, impr_t),
                'branded':     _ctr(clicks_b, impr_b),
                'non_branded': _ctr(clicks_nb, impr_nb),
            },
            'position': {'total': t.get('position', 0)},
        }

    yoy_clicks_t,  yoy_clicks_b,  yoy_clicks_nb  = _split(yoy_total, yoy_branded, 'clicks')
    yoy_impr_t,    yoy_impr_b,    yoy_impr_nb    = _split(yoy_total, yoy_branded, 'impressions')
    yoy_derived = {
        'clicks': {'total': yoy_clicks_t, 'branded': yoy_clicks_b, 'non_branded': yoy_clicks_nb},
        'impressions': {'total': yoy_impr_t, 'branded': yoy_impr_b, 'non_branded': yoy_impr_nb},
        'ctr': {
            'total':       yoy_total.get('ctr', 0) or _ctr(yoy_clicks_t, yoy_impr_t),
            'branded':     _ctr(yoy_clicks_b, yoy_impr_b),
            'non_branded': _ctr(yoy_clicks_nb, yoy_impr_nb),
        },
        'position': {'total': yoy_total.get('position', 0)},
    } if (yoy_total or yoy_branded) else {}

    # ── Columns ─────────────────────────────────────────────────────────────
    range_labels         = [r[2] for r in date_ranges]
    range_labels_display = [
        (f"{lbl} (PR)" if lbl == cur_label else lbl) for lbl in range_labels
    ]
    change_label = 'WOW %' if is_weekly else 'MOM %'
    columns = ['Metric'] + range_labels_display + [change_label]
    if is_monthly:
        columns.append('YOY %')

    def _pct(cur_v, base_v):
        if base_v and base_v != 0:
            return f"{round((cur_v - base_v) / base_v * 100, 1):+.1f}%"
        return 'N/A'

    # Row definition: (display label, metric_key, bucket, is_rate)
    # Avg Position has no branded breakdown — kept as a single Total row.
    row_defs = [
        ('Clicks',                'clicks',      'total',       False),
        ('Branded Clicks',        'clicks',      'branded',     False),
        ('Non-Branded Clicks',    'clicks',      'non_branded', False),
        ('Impressions',           'impressions', 'total',       False),
        ('Branded Impressions',   'impressions', 'branded',     False),
        ('Non-Branded Impressions','impressions','non_branded', False),
        ('CTR',                   'ctr',         'total',       True),
        ('Branded CTR',           'ctr',         'branded',     True),
        ('Non-Branded CTR',       'ctr',         'non_branded', True),
        ('Avg Position',          'position',    'total',       True),
    ]

    # ── Rows (legacy metric-down single table — kept for Excel export) ──────
    rows = []
    for label, mkey, bucket, is_rate in row_defs:
        row = {'Metric': label}
        values_for_change = []
        for lbl_orig, lbl_disp in zip(range_labels, range_labels_display):
            metric_buckets = range_derived.get(lbl_orig, {}).get(mkey, {})
            raw = metric_buckets.get(bucket, 0)
            if is_prorated and lbl_orig == cur_label and not is_rate:
                proj = round(raw * factor)
                row[lbl_disp] = f"{raw} ({proj})"
                values_for_change.append(proj)
            else:
                row[lbl_disp] = raw
                values_for_change.append(raw)

        if len(values_for_change) >= 2:
            row[change_label] = _pct(values_for_change[-1], values_for_change[-2])
        else:
            row[change_label] = 'N/A'

        if is_monthly:
            cur_v = values_for_change[-1] if values_for_change else 0
            yoy_v = yoy_derived.get(mkey, {}).get(bucket) if yoy_derived else None
            row['YOY %'] = _pct(cur_v, yoy_v) if yoy_v is not None else 'N/A'

        rows.append(row)

    # ── Per-metric sub-tables (months-down × Total/Branded/Non-Branded) ─────
    # Front-end renders these as three stacked tables (Clicks, Impressions, CTR)
    # with Months on Y-axis. Avg Position has no branded split so it's skipped.
    def _sub_table(metric_label, total_col_name, mkey, is_rate):
        sub_cols = ['Months', total_col_name, 'Branded', 'Non-Branded']
        sub_rows_out = []
        # series per bucket — used for MoM/WoW/YoY/Total summary rows below
        series = {'total': [], 'branded': [], 'non_branded': []}
        bucket_to_col = [
            ('total',        total_col_name),
            ('branded',     'Branded'),
            ('non_branded', 'Non-Branded'),
        ]
        for lbl_orig, lbl_disp in zip(range_labels, range_labels_display):
            buckets = range_derived.get(lbl_orig, {}).get(mkey, {})
            r = {'Months': lbl_disp}
            for bucket, col_name in bucket_to_col:
                raw = buckets.get(bucket, 0)
                if is_prorated and lbl_orig == cur_label and not is_rate:
                    proj = round(raw * factor)
                    r[col_name] = f"{raw} ({proj})"
                    series[bucket].append(proj)
                else:
                    r[col_name] = raw
                    series[bucket].append(raw)
            sub_rows_out.append(r)

        # MoM / WoW row
        change_row = {'Months': change_label}
        for bucket, col_name in bucket_to_col:
            if len(series[bucket]) >= 2:
                change_row[col_name] = _pct(series[bucket][-1], series[bucket][-2])
            else:
                change_row[col_name] = 'N/A'
        sub_rows_out.append(change_row)

        # YoY row — monthly only
        if is_monthly:
            yoy_row = {'Months': 'YOY %'}
            for bucket, col_name in bucket_to_col:
                yoy_v = (yoy_derived.get(mkey, {}) or {}).get(bucket) if yoy_derived else None
                cur_v = series[bucket][-1] if series[bucket] else 0
                yoy_row[col_name] = _pct(cur_v, yoy_v) if yoy_v is not None else 'N/A'
            sub_rows_out.append(yoy_row)

        # Total row — only for count metrics (sum is meaningless for a rate)
        if not is_rate:
            total_row = {'Months': 'Total'}
            for bucket, col_name in bucket_to_col:
                total_row[col_name] = sum(series[bucket]) if series[bucket] else 0
            sub_rows_out.append(total_row)

        return {
            'title':   metric_label,
            'columns': sub_cols,
            'rows':    sub_rows_out,
        }

    tables = [
        _sub_table('Clicks',      'Total Clicks',      'clicks',      False),
        _sub_table('Impressions', 'Total Impressions', 'impressions', False),
        _sub_table('CTR',         'Total CTR',         'ctr',         True),
    ]

    return {
        'columns':      columns,
        'rows':         rows,
        'total_rows':   len(rows),
        'is_prorated':  is_prorated,
        'days_elapsed': days_elapsed,
        'total_days':   total_days,
        'brand_tokens': brand_tokens,
        # Metric-down summary: rows are pre-grouped (Clicks → Impressions → CTR
        # → Avg Position with Branded/Non-Branded under each). Per-column sort
        # would scramble the grouping, so the front-end honours this flag.
        'unsorted':     True,
        # Three stacked sub-tables (months down, Total/Branded/Non-Branded
        # across) for the on-screen render. Excel export still uses the
        # legacy `rows`/`columns` so its layout is unchanged.
        'tables':       tables,
    }


def _fetch_ga_overview_data(integration, sheet):
    """
    GA Overview — N-period metric-down view. Columns honour sheet.duration:
      Metric | Period_1 | Period_2 | ... | Period_N | MOM%/WOW% | YOY% (monthly only)
    Rows: Sessions, Users, Page Views, Bounce Rate
    Prorate applies only to the current incomplete calendar month (monthly
    schedule). Weekly reports only include complete weeks — no prorate.
    YOY comparison uses the same calendar month one year prior to the last
    period in the result set.
    """
    import calendar as _cal
    from datetime import date as _date
    from integrations.utils.prorate import calculate_prorate_factor
    from integrations.google_oauth import get_credentials_from_integration
    from googleapiclient.discovery import build

    credentials = get_credentials_from_integration(integration)
    if not credentials:
        return {'columns': [], 'rows': [], 'error': 'Invalid credentials'}

    service = build('analyticsdata', 'v1beta', credentials=credentials)
    property_id = integration.provider_id

    order_asc   = sheet.order_by == 'Ascending'
    date_ranges = _get_date_ranges(sheet.schedule, sheet.duration, order_asc, data_lag_days=1)

    if not date_ranges:
        return {'columns': [], 'rows': [], 'total_rows': 0}

    is_monthly = sheet.schedule == 'monthly'
    is_weekly  = sheet.schedule == 'weekly'

    # ── Prorate setup: current calendar month only (monthly schedule) ────────
    today        = _date.today()
    cur_label    = None   # which period label gets the "(PR)" suffix
    factor       = 1.0
    days_elapsed = total_days = None
    if is_monthly:
        for s_dt, _e_dt, lbl in date_ranges:
            if s_dt.year == today.year and s_dt.month == today.month:
                _, last_day  = _cal.monthrange(s_dt.year, s_dt.month)
                cur_full_end = _date(s_dt.year, s_dt.month, last_day)
                days_elapsed, total_days, factor = calculate_prorate_factor(
                    s_dt, cur_full_end, data_lag_days=1
                )
                if factor != 1.0:
                    cur_label = lbl
                break
    is_prorated = factor != 1.0

    ga_metrics     = ['sessions', 'totalUsers', 'screenPageViews', 'bounceRate']
    metric_labels  = ['Sessions', 'Users', 'Page Views', 'Bounce Rate']
    metric_is_rate = [False, False, False, True]

    # ── Fetch each period's metrics in one API call per period ──────────────
    range_values = {}
    api_errors   = []
    for s_dt, e_dt, label in date_ranges:
        try:
            resp = service.properties().runReport(
                property=property_id,
                body={
                    'dateRanges': [{'startDate': s_dt.isoformat(), 'endDate': e_dt.isoformat()}],
                    'metrics':    [{'name': m} for m in ga_metrics],
                }
            ).execute()
            rows = resp.get('rows', [])
            if rows:
                vals = {}
                for i, ml in enumerate(metric_labels):
                    raw = rows[0]['metricValues'][i]['value']
                    vals[ml] = round(float(raw), 2) if '.' in raw else int(raw)
                range_values[label] = vals
            else:
                range_values[label] = {ml: 0 for ml in metric_labels}
        except Exception as e:
            logger.error(f"GA Overview API error ({label}) for sheet {sheet.id}: {e}")
            range_values[label] = {ml: 0 for ml in metric_labels}
            api_errors.append(str(e))

    # ── YOY fetch — monthly only, same calendar month one year prior ────────
    yoy_vals = {}
    if is_monthly:
        cur_s, cur_e, _ = date_ranges[-1]
        yoy_s = _date(cur_s.year - 1, cur_s.month, 1)
        yoy_e = _date(cur_e.year - 1, cur_e.month, cur_e.day)
        try:
            resp = service.properties().runReport(
                property=property_id,
                body={
                    'dateRanges': [{'startDate': yoy_s.isoformat(), 'endDate': yoy_e.isoformat()}],
                    'metrics':    [{'name': m} for m in ga_metrics],
                }
            ).execute()
            rows = resp.get('rows', [])
            if rows:
                for i, ml in enumerate(metric_labels):
                    raw = rows[0]['metricValues'][i]['value']
                    yoy_vals[ml] = round(float(raw), 2) if '.' in raw else int(raw)
        except Exception as e:
            logger.error(f"GA Overview YOY API error for sheet {sheet.id}: {e}")

    if len(api_errors) == len(date_ranges) and api_errors:
        return {'columns': [], 'rows': [], 'total_rows': 0, 'error': f'GA API error: {api_errors[0]}'}

    # ── Column headers — mark current incomplete month with "(PR)" ──────────
    range_labels         = [r[2] for r in date_ranges]
    range_labels_display = [
        (f"{lbl} (PR)" if lbl == cur_label else lbl) for lbl in range_labels
    ]
    change_label = 'WOW %' if is_weekly else 'MOM %'
    columns = ['Metric'] + range_labels_display + [change_label]
    if is_monthly:
        columns.append('YOY %')

    def _pct(cur_v, base_v):
        if base_v and base_v != 0:
            return f"{round((cur_v - base_v) / base_v * 100, 1):+.1f}%"
        return 'N/A'

    # ── Rows: one per metric, one value per period ──────────────────────────
    rows = []
    for ml, is_rate in zip(metric_labels, metric_is_rate):
        row = {'Metric': ml}
        values_for_change = []
        for lbl_orig, lbl_disp in zip(range_labels, range_labels_display):
            raw = range_values.get(lbl_orig, {}).get(ml, 0)
            # Prorate only applies to the current incomplete month AND to
            # count-style metrics. Rate metrics (Bounce Rate) are unchanged.
            if is_prorated and lbl_orig == cur_label and not is_rate:
                proj = round(raw * factor)
                row[lbl_disp] = f"{raw} ({proj})"
                values_for_change.append(proj)
            else:
                row[lbl_disp] = raw
                values_for_change.append(raw)

        # MOM/WOW % — last period vs second-to-last
        if len(values_for_change) >= 2:
            row[change_label] = _pct(values_for_change[-1], values_for_change[-2])
        else:
            row[change_label] = 'N/A'

        # YOY % — monthly only
        if is_monthly:
            cur_v = values_for_change[-1] if values_for_change else 0
            yoy_v = yoy_vals.get(ml)
            row['YOY %'] = _pct(cur_v, yoy_v) if yoy_v is not None else 'N/A'

        rows.append(row)

    return {
        'columns':      columns,
        'rows':         rows,
        'total_rows':   len(rows),
        'is_prorated':  is_prorated,
        'days_elapsed': days_elapsed,
        'total_days':   total_days,
    }


# ── GA Organic Traffic Breakup helpers ─────────────────────────────────────
_BUCKET_TOP_N        = 8     # Number of buckets shown as separate rows; rest → "Other Pages"
_DRILL_TOP_URLS      = 50    # Top URLs per drill-down sub-table (by latest-period sessions)


def _bucket_of_path(path: str) -> str:
    """Return the bucket display name for a URL path (first path segment, prettified)."""
    if not path or path in ('/', ''):
        return 'Home Page'
    cleaned = path.lstrip('/')
    seg = cleaned.split('/', 1)[0] if cleaned else ''
    if not seg:
        return 'Home Page'
    pretty = seg.replace('-', ' ').replace('_', ' ').strip().title()
    return pretty or 'Home Page'


def _drill_topic_of_path(path: str) -> str:
    """
    Return a Category label for drill-down rows — the second path segment
    prettified (matches the client's "Saving & Investment", "Term Insurance"
    style). Empty string when the URL has no second segment.
    """
    cleaned = (path or '').lstrip('/')
    parts = cleaned.split('/')
    if len(parts) >= 2 and parts[1]:
        return parts[1].replace('-', ' ').replace('_', ' ').strip().title()
    return ''


def _fetch_ga_organic_traffic_breakup_data(integration, sheet):
    """
    GA Organic Traffic Breakup — auto-bucketed page-type summary.

    Output is a stacked-tables payload (same shape as GSC Overview) so the
    front-end <SubTable> renderer and the xlsx stacked-tables exporter pick it
    up automatically. Three layers:
      1. Page Type × Months matrix — top buckets (auto-discovered from URL
         data by first path segment). Buckets beyond top-N collapse into
         "Other Pages".
      2. Per-bucket drill-down tables — second-segment topic rollup, then a
         per-URL list (top 50 by latest-period sessions).
    Bucket discovery is purely URL-structural — no per-domain/industry list
    is hard-coded, so the same fetcher works for every project.

    Prorate applies to the current incomplete calendar month (monthly only).
    Weekly schedules are complete-only — no prorate.
    YOY column added monthly only, comparing the rightmost period to the same
    calendar month one year prior.
    """
    import calendar as _cal
    from datetime import date as _date
    from integrations.utils.prorate import calculate_prorate_factor
    from integrations.google_oauth import get_credentials_from_integration
    from googleapiclient.discovery import build

    credentials = get_credentials_from_integration(integration)
    if not credentials:
        return {'columns': [], 'rows': [], 'error': 'Invalid credentials'}

    service     = build('analyticsdata', 'v1beta', credentials=credentials)
    property_id = integration.provider_id

    order_asc   = sheet.order_by == 'Ascending'
    date_ranges = _get_date_ranges(sheet.schedule, sheet.duration, order_asc, data_lag_days=1)
    if not date_ranges:
        return {'columns': [], 'rows': [], 'total_rows': 0}

    is_monthly = sheet.schedule == 'monthly'
    is_weekly  = sheet.schedule == 'weekly'

    # ── Prorate setup: current calendar month only (monthly schedule) ───────
    today        = _date.today()
    cur_label    = None
    factor       = 1.0
    days_elapsed = total_days = None
    if is_monthly:
        for s_dt, _e_dt, lbl in date_ranges:
            if s_dt.year == today.year and s_dt.month == today.month:
                _, last_day  = _cal.monthrange(s_dt.year, s_dt.month)
                cur_full_end = _date(s_dt.year, s_dt.month, last_day)
                days_elapsed, total_days, factor = calculate_prorate_factor(
                    s_dt, cur_full_end, data_lag_days=1
                )
                if factor != 1.0:
                    cur_label = lbl
                break
    is_prorated = factor != 1.0

    organic_filter = {
        'filter': {
            'fieldName':    'sessionDefaultChannelGroup',
            'stringFilter': {'value': 'Organic Search', 'matchType': 'EXACT'},
        }
    }

    def _runReport(start_dt, end_dt, dim='pagePath', limit=10000):
        body = {
            'dateRanges':      [{'startDate': start_dt.isoformat(), 'endDate': end_dt.isoformat()}],
            'dimensions':      [{'name': dim}],
            'metrics':         [{'name': 'sessions'}],
            'dimensionFilter': organic_filter,
            'limit':           limit,
        }
        return service.properties().runReport(property=property_id, body=body).execute()

    # ── Fetch per-period page paths ─────────────────────────────────────────
    range_paths = {}     # {label: [(path, sessions), ...]}
    api_errors  = []
    for s_dt, e_dt, label in date_ranges:
        try:
            resp = _runReport(s_dt, e_dt)
            entries = []
            for r in resp.get('rows', []):
                path = r['dimensionValues'][0]['value']
                sess = int(r['metricValues'][0]['value'])
                entries.append((path, sess))
            range_paths[label] = entries
        except Exception as e:
            logger.error(f"GA Breakup API error ({label}) for sheet {sheet.id}: {e}")
            range_paths[label] = []
            api_errors.append(str(e))

    # ── YOY fetch — monthly only ────────────────────────────────────────────
    yoy_paths = []
    if is_monthly and date_ranges:
        cur_s, cur_e, _ = date_ranges[-1]
        yoy_s = _date(cur_s.year - 1, cur_s.month, cur_s.day)
        yoy_e = _date(cur_e.year - 1, cur_e.month, cur_e.day)
        try:
            resp = _runReport(yoy_s, yoy_e)
            for r in resp.get('rows', []):
                yoy_paths.append((
                    r['dimensionValues'][0]['value'],
                    int(r['metricValues'][0]['value']),
                ))
        except Exception as e:
            logger.error(f"GA Breakup YOY API error for sheet {sheet.id}: {e}")

    if api_errors and len(api_errors) == len(date_ranges):
        return {
            'columns': [], 'rows': [], 'total_rows': 0,
            'error':   f'GA API error: {api_errors[0]}',
        }

    # ── Bucket aggregation ──────────────────────────────────────────────────
    # bucket_period_sessions[bucket][label] = sum of sessions for that bucket/period
    # bucket_paths[bucket][label] = [(path, sessions), ...]
    from collections import defaultdict
    bucket_period_sessions = defaultdict(lambda: defaultdict(int))
    bucket_paths           = defaultdict(lambda: defaultdict(list))

    for label, entries in range_paths.items():
        for path, sess in entries:
            bucket = _bucket_of_path(path)
            bucket_period_sessions[bucket][label] += sess
            bucket_paths[bucket][label].append((path, sess))

    yoy_bucket = defaultdict(int)
    for path, sess in yoy_paths:
        yoy_bucket[_bucket_of_path(path)] += sess

    # Pick top-N buckets by total sessions across all periods. Always keep
    # "Home Page" pinned at the top if present.
    bucket_totals = {b: sum(v.values()) for b, v in bucket_period_sessions.items()}
    sorted_buckets = sorted(bucket_totals.items(), key=lambda kv: kv[1], reverse=True)
    top_buckets = []
    if 'Home Page' in bucket_totals:
        top_buckets.append('Home Page')
    for b, _ in sorted_buckets:
        if b == 'Home Page':
            continue
        if len(top_buckets) >= _BUCKET_TOP_N:
            break
        top_buckets.append(b)
    rest_buckets = [b for b in bucket_totals if b not in top_buckets]

    # ── Section 1: Page Type × Months matrix ────────────────────────────────
    range_labels         = [r[2] for r in date_ranges]
    range_labels_display = [
        (f"{lbl} (PR)" if lbl == cur_label else lbl) for lbl in range_labels
    ]
    change_label = 'WOW %' if is_weekly else 'MOM %'
    period_cols  = list(range_labels_display)
    section1_cols = ['Page Type'] + period_cols + [change_label]
    if is_monthly:
        section1_cols.append('YOY %')

    def _pct(cur_v, base_v):
        if base_v and base_v != 0:
            return f"{round((cur_v - base_v) / base_v * 100, 1):+.1f}%"
        return 'N/A'

    def _cell_for(raw, lbl_orig):
        """Apply prorate to the current-month cell, else return raw."""
        if is_prorated and lbl_orig == cur_label:
            proj = round(raw * factor)
            return f"{raw} ({proj})", proj
        return raw, raw

    section1_rows = []
    for bucket in top_buckets:
        row = {'Page Type': bucket}
        change_series = []
        for lbl_orig, lbl_disp in zip(range_labels, range_labels_display):
            raw = bucket_period_sessions.get(bucket, {}).get(lbl_orig, 0)
            display, numeric = _cell_for(raw, lbl_orig)
            row[lbl_disp] = display
            change_series.append(numeric)
        row[change_label] = (
            _pct(change_series[-1], change_series[-2])
            if len(change_series) >= 2 else 'N/A'
        )
        if is_monthly:
            cur_v = change_series[-1] if change_series else 0
            yoy_v = yoy_bucket.get(bucket)
            row['YOY %'] = _pct(cur_v, yoy_v) if yoy_v is not None else 'N/A'
        section1_rows.append(row)

    # "Other Pages" rollup row — sum of every bucket not in top_buckets
    if rest_buckets:
        other_row = {'Page Type': 'Other Pages'}
        change_series = []
        for lbl_orig, lbl_disp in zip(range_labels, range_labels_display):
            raw = sum(bucket_period_sessions.get(b, {}).get(lbl_orig, 0)
                      for b in rest_buckets)
            display, numeric = _cell_for(raw, lbl_orig)
            other_row[lbl_disp] = display
            change_series.append(numeric)
        other_row[change_label] = (
            _pct(change_series[-1], change_series[-2])
            if len(change_series) >= 2 else 'N/A'
        )
        if is_monthly:
            cur_v = change_series[-1] if change_series else 0
            yoy_v = sum(yoy_bucket.get(b, 0) for b in rest_buckets) or None
            other_row['YOY %'] = _pct(cur_v, yoy_v) if yoy_v else 'N/A'
        section1_rows.append(other_row)

    tables = [{
        'title':   'Organic Traffic Analysis (GA4)',
        'columns': section1_cols,
        'rows':    section1_rows,
    }]

    # ── Drill-down tables per top bucket (skip "Home Page") ─────────────────
    for bucket in top_buckets:
        if bucket == 'Home Page':
            continue

        # Per-URL aggregation for this bucket: {path: {label: sessions}}
        per_url = defaultdict(lambda: defaultdict(int))
        for label in range_labels:
            for path, sess in bucket_paths.get(bucket, {}).get(label, []):
                per_url[path][label] += sess

        if not per_url:
            continue

        # YOY per-URL — for the same calendar month one year prior to last period
        yoy_per_url = defaultdict(int)
        for path, sess in yoy_paths:
            if _bucket_of_path(path) == bucket:
                yoy_per_url[path] += sess

        # Sort URLs by latest period sessions, take top N
        latest_label = range_labels[-1]
        sorted_urls = sorted(
            per_url.items(),
            key=lambda kv: kv[1].get(latest_label, 0),
            reverse=True,
        )[:_DRILL_TOP_URLS]

        sub_cols = ['Page URL', 'Category'] + period_cols + [change_label]
        if is_monthly:
            sub_cols.append('YOY %')
        sub_rows = []
        for path, period_sess in sorted_urls:
            row = {
                'Page URL': path,
                'Category': _drill_topic_of_path(path),
            }
            change_series = []
            for lbl_orig, lbl_disp in zip(range_labels, range_labels_display):
                raw = period_sess.get(lbl_orig, 0)
                display, numeric = _cell_for(raw, lbl_orig)
                row[lbl_disp] = display
                change_series.append(numeric)
            row[change_label] = (
                _pct(change_series[-1], change_series[-2])
                if len(change_series) >= 2 else 'N/A'
            )
            if is_monthly:
                cur_v = change_series[-1] if change_series else 0
                yoy_v = yoy_per_url.get(path)
                row['YOY %'] = _pct(cur_v, yoy_v) if yoy_v is not None else 'N/A'
            sub_rows.append(row)

        tables.append({
            'title':   bucket,
            'columns': sub_cols,
            'rows':    sub_rows,
        })

    # ── Legacy single-table flat shape (kept for any caller that expects it) ─
    # Re-uses Section 1's data so Excel fallback paths still work.
    legacy_columns = section1_cols
    legacy_rows    = section1_rows

    return {
        'columns':      legacy_columns,
        'rows':         legacy_rows,
        'total_rows':   len(legacy_rows),
        'is_prorated':  is_prorated,
        'days_elapsed': days_elapsed,
        'total_days':   total_days,
        'unsorted':     True,
        'tables':       tables,
    }


def _fetch_ga_gsc_reconciliation_data(ga_integration, gsc_integration, sheet):
    """
    GA vs GSC Reconciliation — one row per period showing:
      - Sessions: GA Organic Search sessions (site-wide)
      - Clicks: GSC total clicks (site-wide)
      - Clicks to Sessions Ratio: Sessions ÷ Clicks (how much of GSC-reported traffic
        GA is capturing as Organic sessions; 1.0 means perfect match)
    Monthly schedule prorates the current incomplete month (raw shown alongside
    projected value and the label suffixed with " (PR)").
    """
    import calendar as _cal
    from datetime import date as _date
    from integrations.utils.prorate import calculate_prorate_factor
    from integrations.google_oauth import get_credentials_from_integration
    from googleapiclient.discovery import build

    order_asc = sheet.order_by == 'Ascending'
    # GA has ~1-day reporting lag, GSC has ~3-day lag. Use each provider's
    # natural lag so the raw values shown match what the user sees in GA/GSC
    # UI for the same period. For the current incomplete month the end dates
    # will differ slightly (e.g. GA Apr 1-26 vs GSC Apr 1-24); proration
    # projects both to the full calendar month for an apples-to-apples ratio.
    ga_ranges  = _get_date_ranges(sheet.schedule, sheet.duration, order_asc, data_lag_days=1)
    gsc_ranges = _get_date_ranges(sheet.schedule, sheet.duration, order_asc, data_lag_days=3)

    ga_creds = get_credentials_from_integration(ga_integration)
    if not ga_creds:
        return {'columns': [], 'rows': [], 'error': 'Invalid GA credentials'}
    gsc_creds = get_credentials_from_integration(gsc_integration)
    if not gsc_creds:
        return {'columns': [], 'rows': [], 'error': 'Invalid GSC credentials'}

    ga_service  = build('analyticsdata', 'v1beta', credentials=ga_creds)
    gsc_service = build('searchconsole', 'v1', credentials=gsc_creds)
    property_id = ga_integration.provider_id
    site_url    = gsc_integration.provider_id

    # ── Prorate setup: only the current calendar month (monthly schedule) ────
    # GA and GSC are prorated independently using their own lag so the raw
    # value in the cell matches each provider's UI for the dates fetched.
    is_monthly = sheet.schedule == 'monthly'
    today      = _date.today()
    cur_label  = None
    ga_factor  = gsc_factor = 1.0
    ga_days_elapsed  = ga_total_days  = None
    gsc_days_elapsed = gsc_total_days = None
    if is_monthly:
        for s_dt, _e_dt, lbl in ga_ranges:
            if s_dt.year == today.year and s_dt.month == today.month:
                _, last_day  = _cal.monthrange(s_dt.year, s_dt.month)
                cur_full_end = _date(s_dt.year, s_dt.month, last_day)
                ga_days_elapsed,  ga_total_days,  ga_factor  = calculate_prorate_factor(s_dt, cur_full_end, data_lag_days=1)
                gsc_days_elapsed, gsc_total_days, gsc_factor = calculate_prorate_factor(s_dt, cur_full_end, data_lag_days=3)
                if ga_factor != 1.0 or gsc_factor != 1.0:
                    cur_label = lbl
                break
    is_prorated = (ga_factor != 1.0) or (gsc_factor != 1.0)

    # Match the dimension shown in the GA UI's Traffic acquisition report —
    # "Session primary channel group" (sessionPrimaryChannelGroup). The
    # previous default-channel-group filter could under-report Organic Search
    # in properties that customize their primary channel group.
    organic_filter = {
        'filter': {
            'fieldName': 'sessionPrimaryChannelGroup',
            'stringFilter': {'value': 'Organic Search', 'matchType': 'EXACT'},
        }
    }

    range_data = {}   # {label: {'sessions': int, 'clicks': int}}
    api_errors = []

    # ga_ranges and gsc_ranges share the same labels and start dates; only the
    # current period's end date differs (each uses its own provider lag).
    for (ga_start, ga_end, label), (_gsc_start, gsc_end, _gsc_label) in zip(ga_ranges, gsc_ranges):
        # GA Organic Sessions (site-wide, no dimension)
        try:
            ga_resp = ga_service.properties().runReport(
                property=property_id,
                body={
                    'dateRanges':      [{'startDate': ga_start.isoformat(), 'endDate': ga_end.isoformat()}],
                    'metrics':         [{'name': 'sessions'}],
                    'dimensionFilter': organic_filter,
                }
            ).execute()
            ga_rows = ga_resp.get('rows', [])
            sessions = int(ga_rows[0]['metricValues'][0]['value']) if ga_rows else 0
        except Exception as e:
            logger.error(f"Reconcile GA error ({label}) for sheet {sheet.id}: {e}")
            sessions = 0
            api_errors.append(f'GA: {e}')

        # GSC Clicks (site-wide totals, no dimensions)
        try:
            gsc_resp = gsc_service.searchanalytics().query(
                siteUrl=site_url,
                body={
                    'startDate': ga_start.isoformat(),
                    'endDate':   gsc_end.isoformat(),
                    'rowLimit':  1,
                }
            ).execute()
            gsc_rows = gsc_resp.get('rows', [])
            clicks = int(gsc_rows[0].get('clicks', 0)) if gsc_rows else 0
        except Exception as e:
            logger.error(f"Reconcile GSC error ({label}) for sheet {sheet.id}: {e}")
            clicks = 0
            api_errors.append(f'GSC: {e}')

        range_data[label] = {'sessions': sessions, 'clicks': clicks}

    # If EVERY period failed for both APIs, surface an error.
    if not range_data and api_errors:
        return {'columns': [], 'rows': [], 'total_rows': 0, 'error': api_errors[0]}

    columns = ['Sr No', 'Month', 'Sessions', 'Clicks', 'Clicks to Sessions Ratio']

    rows = []
    for idx, (_s, _e, label) in enumerate(ga_ranges, 1):
        data = range_data.get(label, {'sessions': 0, 'clicks': 0})
        raw_s = data['sessions']
        raw_c = data['clicks']

        if is_prorated and label == cur_label:
            proj_s = round(raw_s * ga_factor)
            proj_c = round(raw_c * gsc_factor)
            sessions_cell = f"{raw_s} ({proj_s})"
            clicks_cell   = f"{raw_c} ({proj_c})"
            ratio_s, ratio_c = proj_s, proj_c
            month_label = f"{label} (PR)"
        else:
            sessions_cell = raw_s
            clicks_cell   = raw_c
            ratio_s, ratio_c = raw_s, raw_c
            month_label = label

        if ratio_c:
            ratio_cell = round(ratio_s / ratio_c, 4)
        else:
            ratio_cell = 'N/A'

        rows.append({
            'Sr No':                     idx,
            'Month':                     month_label,
            'Sessions':                  sessions_cell,
            'Clicks':                    clicks_cell,
            'Clicks to Sessions Ratio':  ratio_cell,
        })

    return {
        'columns':          columns,
        'rows':             rows,
        'total_rows':       len(rows),
        'is_prorated':      is_prorated,
        'ga_days_elapsed':  ga_days_elapsed,
        'gsc_days_elapsed': gsc_days_elapsed,
        'total_days':       ga_total_days or gsc_total_days,
    }


def _get_weekly_ranges(data_lag_days=3):
    """
    Compute the current partial week and previous complete week.
    Returns (prv_start, prv_end, prv_label, cur_start, cur_end_api, cur_label,
             cur_full_end, yoy_start, yoy_end).
    data_lag_days defaults to 3 (GSC reporting lag); pass 1 for GA.
    """
    from datetime import date as _date
    today = _date.today() - timedelta(days=data_lag_days)
    days_since_sunday = (today.weekday() + 1) % 7
    last_sunday = today - timedelta(days=days_since_sunday)
    cur_start    = last_sunday + timedelta(days=1)
    cur_end_api  = today
    cur_full_end = cur_start + timedelta(days=6)
    # Previous complete week
    prv_end   = last_sunday
    prv_start = prv_end - timedelta(days=6)
    prv_label = f"{prv_start.strftime('%d %b')}-{prv_end.strftime('%d %b')}"
    has_partial = cur_start <= today
    if has_partial:
        cur_label = f"{cur_start.strftime('%d %b')}-{cur_end_api.strftime('%d %b')}"
    else:
        # Today is Sunday — no partial; use last 2 complete weeks
        cur_start    = prv_start
        cur_end_api  = prv_end
        cur_full_end = prv_end
        cur_label    = prv_label
        prv_end   = prv_start - timedelta(days=1)
        prv_start = prv_end - timedelta(days=6)
        prv_label = f"{prv_start.strftime('%d %b')}-{prv_end.strftime('%d %b')}"
    # YOY: same calendar dates last year
    yoy_start = _date(cur_start.year - 1, cur_start.month, cur_start.day)
    yoy_end   = _date(cur_end_api.year - 1, cur_end_api.month, cur_end_api.day)
    return (prv_start, prv_end, prv_label,
            cur_start, cur_end_api, cur_label, cur_full_end,
            yoy_start, yoy_end)



def _fetch_domain_metrics_data(domain_id, sheet):
    """
    Domain Metrics — show ranking distribution over time from
    SeoDomainDailyMetrics (top-1, top-3, top-10, etc.) similar to how
    RankMaxx shows DA/DR from DomainTracking.
    """
    order_asc = sheet.order_by == 'Ascending'
    date_ranges = _get_date_ranges(sheet.schedule, sheet.duration, order_asc)
    change_units = sheet.change_units or []

    range_labels = [r[2] for r in date_ranges]

    metric_defs = [
        ('Top 1 Keywords', 'top_1_count'),
        ('Top 3 Keywords', 'top_3_count'),
        ('Top 10 Keywords', 'top_10_count'),
        ('Top 50 Keywords', 'top_50_count'),
        ('Top 100 Keywords', 'top_100_count'),
        ('Not Ranked', 'not_ranked_count'),
        ('Rankmax Score', 'score_meter'),
    ]

    range_values = {}
    for start_dt, end_dt, label in date_ranges:
        metric = SeoDomainDailyMetrics.objects.filter(
            domain_id=domain_id,
            snapshot_date__gte=start_dt,
            snapshot_date__lte=end_dt,
        ).order_by('-snapshot_date').first()

        if metric:
            range_values[label] = {
                'top_1_count': metric.top_1_count,
                'top_3_count': metric.top_3_count,
                'top_10_count': metric.top_10_count,
                'top_50_count': metric.top_50_count,
                'top_100_count': metric.top_100_count,
                'not_ranked_count': metric.not_ranked_count,
                'score_meter': float(metric.score_meter),
            }
        else:
            range_values[label] = {k: 0 for _, k in metric_defs}

    columns = ['Metric']
    for rl in range_labels:
        columns.append(rl)
    if len(range_labels) >= 2 and 'number' in change_units:
        columns.append('Change')
    if len(range_labels) >= 2 and 'percentage' in change_units:
        columns.append('Change (%)')

    rows = []
    for label, key in metric_defs:
        row = {'Metric': label}
        values = []
        for rl in range_labels:
            val = range_values.get(rl, {}).get(key, 0)
            row[rl] = val
            values.append(val)
        if len(values) >= 2:
            diff = round(values[-1] - values[-2], 2)
            if 'number' in change_units:
                row['Change'] = diff
            if 'percentage' in change_units:
                pct = round((diff / values[-2]) * 100, 2) if values[-2] != 0 else 0
                row['Change (%)'] = f"{pct}%"
        rows.append(row)

    return {'columns': columns, 'rows': rows, 'total_rows': len(rows)}


def _fetch_keyword_ranking_overview(domain_id, sheet):
    """
    Keyword Ranking Overview — current ranking distribution snapshot,
    similar to RankMaxx keyword_monthly_ranking_report.
    """
    kws = SeoKeywordRank.objects.filter(domain_id=domain_id)
    total = kws.count()
    if total == 0:
        return {
            'columns': ['Metric', 'Count', 'Percentage'],
            'rows': [{'Metric': 'No keywords tracked', 'Count': 0, 'Percentage': '0%'}],
            'total_rows': 1,
        }

    from django.db.models import Q, Count

    buckets = [
        ('Top 1', Q(rank_now=1)),
        ('Top 3', Q(rank_now__gte=1, rank_now__lte=3)),
        ('Top 5', Q(rank_now__gte=1, rank_now__lte=5)),
        ('Top 10', Q(rank_now__gte=1, rank_now__lte=10)),
        ('Top 20', Q(rank_now__gte=1, rank_now__lte=20)),
        ('Top 50', Q(rank_now__gte=1, rank_now__lte=50)),
        ('Top 100', Q(rank_now__gte=1, rank_now__lte=100)),
        ('Not Ranked', Q(rank_now=0) | Q(rank_now__isnull=True)),
        ('Improved (1D)', Q(day_mark='up')),
        ('Declined (1D)', Q(day_mark='down')),
    ]

    rows = []
    for idx, (label, q_filter) in enumerate(buckets, 1):
        cnt = kws.filter(q_filter).count()
        pct = round(cnt / total * 100, 1) if total > 0 else 0
        rows.append({'Sr No': idx, 'Metric': label, 'Count': cnt, 'Percentage': f"{pct}%"})

    return {
        'columns': ['Sr No', 'Metric', 'Count', 'Percentage'],
        'rows': rows,
        'total_rows': len(rows),
    }


def _ordinal_convert(n):
    """Convert day number to ordinal: 1->1st, 2->2nd, 3->3rd, 4->4th, etc."""
    return f"{n:d}{'tsnrhtdd'[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4]}"


def _ordinal_day_convert(d):
    """Convert a date to format like '2nd Mar', '9th Mar'."""
    return f"{_ordinal_convert(d.day)} {d.strftime('%b')}"


def _classify_rank(rank):
    """Classify rank into reporting brackets."""
    if 1 <= rank <= 5:
        return 'Top 5'
    elif 6 <= rank <= 10:
        return 'Top 6 - 10'
    elif 11 <= rank <= 20:
        return 'Top 11 - 20'
    elif 21 <= rank <= 30:
        return 'Top 21 - 30'
    elif 31 <= rank <= 50:
        return 'Top 31 - 50'
    else:
        return 'Above 50'


def _fetch_keyword_ranking_weekly(domain_id, sheet):
    """
    Keyword Ranking Weekly report — shows ranking values at weekly intervals
    with date columns like '2nd Mar', '9th Mar' and change calculations.
    Mirrors RankMaxx keyword_ranking_report().
    """
    from django.db.models import Q
    from collections import defaultdict

    duration_limit = sheet.duration or 2
    kw_metrics = sheet.metrics or []
    order_asc = sheet.order_by.lower() in ('ascending', 'asc')

    # Get keywords for this domain
    kws = list(
        SeoKeywordRank.objects.select_related('keyword').filter(
            domain_id=domain_id
        ).order_by('keyword__keyword')[:500]
    )
    if not kws:
        return {'columns': [], 'rows': [], 'total_rows': 0, 'overview': []}

    # Determine the most recent ranked date across all keywords
    last_ranked = None
    for kw in kws:
        if kw.last_ranked_date:
            d = kw.last_ranked_date.date() if hasattr(kw.last_ranked_date, 'date') else kw.last_ranked_date
            if last_ranked is None or d > last_ranked:
                last_ranked = d

    if not last_ranked:
        last_ranked = date.today()

    # Calculate weekly column dates (default tracking day = Monday)
    today_weekday = last_ranked.weekday()  # 0=Monday
    target_day = 0  # Monday
    remain_count = (today_weekday - target_day + 7) % 7

    week_dates = []
    for i in range(duration_limit):
        week_date = last_ranked - timedelta(days=remain_count + 7 * i)
        week_dates.append(week_date)

    # Labels for each week column
    week_labels = [_ordinal_day_convert(d) for d in week_dates]

    # Fetch rank history for all keywords at the relevant date range
    min_date = week_dates[-1] - timedelta(days=3) if week_dates else last_ranked - timedelta(days=90)
    max_date = week_dates[0] + timedelta(days=3) if week_dates else last_ranked

    kw_ids = [kw.id for kw in kws]

    history_qs = SeoRankHistory.objects.filter(
        seo_keyword_rank_id__in=kw_ids,
        snapshot_date__gte=min_date,
        snapshot_date__lte=max_date,
    ).values_list('seo_keyword_rank_id', 'snapshot_date', 'rank_position')

    # Build lookup: {kw_id: {date: rank}}
    history_map = defaultdict(dict)
    for kw_id, snap_date, rank_pos in history_qs:
        history_map[kw_id][snap_date] = rank_pos

    def _get_rank_for_date(kw_id, target_date):
        """Get rank at target_date, or try ±1-3 days."""
        h = history_map.get(kw_id, {})
        if target_date in h:
            return h[target_date]
        for offset in [1, -1, 2, -2, 3, -3]:
            d = target_date + timedelta(days=offset)
            if d in h:
                return h[d]
        return None

    # Build columns
    columns = ['Sr No', 'Keywords']
    if 'average_volume' in kw_metrics:
        columns.append('Avg. Volume')
    if 'landing_pages' in kw_metrics:
        columns.append('Landing Pages')
    if 'base_ranking' in kw_metrics:
        columns.append('Base Ranking')

    # Add week date columns (ordered oldest to newest if asc, newest to oldest if desc)
    ordered_labels = list(reversed(week_labels)) if order_asc else week_labels
    ordered_dates = list(reversed(week_dates)) if order_asc else week_dates
    columns.extend(ordered_labels)

    # Change column
    if len(week_labels) >= 2:
        change_label = f"Change ({week_labels[0]} vs {week_labels[1]})"
        columns.append(change_label)
    else:
        change_label = None

    # Build rows
    rows = []
    for idx, kw in enumerate(kws, 1):
        kw_text = kw.keyword.keyword if kw.keyword else ''
        row = {'Sr No': idx, 'Keywords': kw_text}

        if 'average_volume' in kw_metrics:
            row['Avg. Volume'] = kw.search_volume if kw.search_volume else '-'
        if 'landing_pages' in kw_metrics:
            if kw.site_url and kw.rank_now and kw.rank_now > 0:
                row['Landing Pages'] = kw.site_url
            else:
                row['Landing Pages'] = ''
        if 'base_ranking' in kw_metrics:
            row['Base Ranking'] = kw.rank_since_start if kw.rank_since_start and kw.rank_since_start > 0 else 100

        # Fill in week ranking values
        rank_values = {}
        for i, (wd, wl) in enumerate(zip(week_dates, week_labels)):
            rank = _get_rank_for_date(kw.id, wd)
            if rank is not None and rank > 0:
                rank_values[wl] = rank
            else:
                rank_values[wl] = 'NA'

        for label in ordered_labels:
            row[label] = rank_values.get(label, 'NA')

        # Calculate change between most recent two weeks
        if change_label and len(week_labels) >= 2:
            curr = rank_values.get(week_labels[0], 'NA')
            prev = rank_values.get(week_labels[1], 'NA')
            if isinstance(curr, int) and isinstance(prev, int):
                row[change_label] = prev - curr  # positive = improved
            else:
                row[change_label] = 'NA'

        rows.append(row)

    # Build overview: keyword count per rank bracket per week
    brackets = ['Top 5', 'Top 6 - 10', 'Top 11 - 20', 'Top 21 - 30', 'Top 31 - 50', 'Above 50']
    overview_rows = []
    for bracket in brackets:
        ov_row = {'primary keyword ranking': bracket}
        if 'base_ranking' in kw_metrics:
            # Base ranking bracket count
            base_count = sum(
                1 for kw in kws
                if _classify_rank(kw.rank_since_start if kw.rank_since_start and kw.rank_since_start > 0 else 100) == bracket
            )
            ov_row['Base Ranking'] = base_count

        for wd, wl in zip(week_dates, week_labels):
            count = 0
            for kw in kws:
                rank = _get_rank_for_date(kw.id, wd)
                if rank and rank > 0 and _classify_rank(rank) == bracket:
                    count += 1
            ov_row[wl] = count
        overview_rows.append(ov_row)

    # Add change column to overview
    if change_label and len(week_labels) >= 2:
        for ov_row in overview_rows:
            curr_val = ov_row.get(week_labels[0], 0)
            prev_val = ov_row.get(week_labels[1], 0)
            ov_row[change_label] = curr_val - prev_val

    # Total row
    total_row = {'primary keyword ranking': 'Total keywords'}
    for key in overview_rows[0]:
        if key != 'primary keyword ranking':
            total_row[key] = sum(r.get(key, 0) for r in overview_rows if isinstance(r.get(key), int))
    overview_rows.append(total_row)

    return {
        'columns': columns,
        'rows': rows,
        'total_rows': len(rows),
        'overview': overview_rows,
    }


def _fetch_keyword_ranking_monthly(domain_id, sheet):
    """
    Keyword Ranking Monthly report — shows ranking values at monthly intervals
    with date columns like 'Mar/2024', 'Feb/2024' and MOM Change.
    Mirrors RankMaxx keyword_monthly_ranking_report().
    """
    from collections import defaultdict
    import calendar

    duration_limit = sheet.duration or 2
    kw_metrics = sheet.metrics or []
    order_asc = sheet.order_by.lower() in ('ascending', 'asc')

    kws = list(
        SeoKeywordRank.objects.select_related('keyword').filter(
            domain_id=domain_id
        ).order_by('keyword__keyword')[:500]
    )
    if not kws:
        return {'columns': [], 'rows': [], 'total_rows': 0}

    # Calculate monthly sample dates (4th of each month, like RankMaxx)
    today = date.today()
    month_dates = []
    for i in range(duration_limit):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        sample_date = date(year, month, 4)
        month_dates.append(sample_date)

    month_labels = [d.strftime('%b/%Y') for d in month_dates]

    # Fetch rank history
    kw_ids = [kw.id for kw in kws]
    min_date = month_dates[-1] - timedelta(days=5) if month_dates else today - timedelta(days=365)
    max_date = month_dates[0] + timedelta(days=5) if month_dates else today

    history_qs = SeoRankHistory.objects.filter(
        seo_keyword_rank_id__in=kw_ids,
        snapshot_date__gte=min_date,
        snapshot_date__lte=max_date,
    ).values_list('seo_keyword_rank_id', 'snapshot_date', 'rank_position')

    history_map = defaultdict(dict)
    for kw_id, snap_date, rank_pos in history_qs:
        history_map[kw_id][snap_date] = rank_pos

    def _get_rank_for_date(kw_id, target_date):
        h = history_map.get(kw_id, {})
        if target_date in h:
            return h[target_date]
        for offset in [1, -1, 2, -2, 3, -3, 4, -4, 5, -5]:
            d = target_date + timedelta(days=offset)
            if d in h:
                return h[d]
        return None

    # Build columns
    columns = ['Sr No', 'Keywords']
    if 'average_volume' in kw_metrics:
        columns.append('Avg. Volume')
    if 'landing_pages' in kw_metrics:
        columns.append('Landing Pages')
    if 'base_ranking' in kw_metrics:
        columns.append('Base Ranking')

    ordered_labels = list(reversed(month_labels)) if order_asc else month_labels
    ordered_dates = list(reversed(month_dates)) if order_asc else month_dates
    columns.extend(ordered_labels)
    columns.append('MOM Change')

    # Build rows
    rows = []
    for idx, kw in enumerate(kws, 1):
        kw_text = kw.keyword.keyword if kw.keyword else ''
        row = {'Sr No': idx, 'Keywords': kw_text}

        if 'average_volume' in kw_metrics:
            row['Avg. Volume'] = kw.search_volume if kw.search_volume else '-'
        if 'landing_pages' in kw_metrics:
            if kw.site_url and kw.rank_now and kw.rank_now > 0:
                row['Landing Pages'] = kw.site_url
            else:
                row['Landing Pages'] = ''
        if 'base_ranking' in kw_metrics:
            row['Base Ranking'] = kw.rank_since_start if kw.rank_since_start and kw.rank_since_start > 0 else 100

        # Fill in monthly ranking values
        rank_values = {}
        for md, ml in zip(month_dates, month_labels):
            rank = _get_rank_for_date(kw.id, md)
            if rank is not None and rank > 0:
                rank_values[ml] = rank
            else:
                rank_values[ml] = 'NA'

        for label in ordered_labels:
            row[label] = rank_values.get(label, 'NA')

        # MOM Change: most recent month rank vs previous month rank
        if len(month_labels) >= 2:
            curr = rank_values.get(month_labels[0], 'NA')
            prev = rank_values.get(month_labels[1], 'NA')
            if isinstance(curr, int) and isinstance(prev, int):
                row['MOM Change'] = prev - curr  # positive = improved
            else:
                row['MOM Change'] = 'NA'
        else:
            row['MOM Change'] = 'NA'

        rows.append(row)

    return {
        'columns': columns,
        'rows': rows,
        'total_rows': len(rows),
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_report_sheet_data(request):
    """
    Fetch live data for all report sheets of a domain.
    Query params: domain_id (required)
    Returns report data for each configured sheet.
    """
    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id required'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_ids = list(_get_user_domain_ids(request.user))
    if int(domain_id) not in allowed_ids:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    sheets = SeoReportSheet.objects.filter(
        domain_id=domain_id, is_active=True
    ).order_by('-created_at')

    if not sheets.exists():
        return Response({'reports': [], 'count': 0})

    # Get integrations for this domain
    from integrations.models import Integration

    gsc_integration = Integration.objects.filter(
        domain_id=domain_id, type='search_console', status='active'
    ).exclude(provider_id='').exclude(provider_id='pending_selection').exclude(provider_id__isnull=True).first()

    ga_integration = Integration.objects.filter(
        domain_id=domain_id, type='google_analytics', status='active'
    ).exclude(provider_id='').exclude(provider_id='pending_selection').exclude(provider_id__isnull=True).first()

    reports = []
    for sheet in sheets:
        report_entry = {
            'sheet_id': sheet.id,
            'sheet_name': sheet.sheet_name,
            'sheet_type': sheet.sheet_type,
            'category': sheet.category,
            'schedule': sheet.schedule,
            'duration': sheet.duration,
            'order_by': sheet.order_by,
            'metrics': sheet.metrics,
            'change_units': sheet.change_units,
            'columns': [],
            'rows': [],
            'total_rows': 0,
            'error': None,
        }

        try:
            if sheet.category == 'gsc' and sheet.sheet_type in (
                'gsc_pages', 'gsc_branded_queries', 'gsc_non_branded_queries', 'gsc_queries'
            ):
                if not gsc_integration:
                    report_entry['error'] = 'Google Search Console not connected'
                else:
                    data = _fetch_gsc_report_data(gsc_integration, sheet)
                    report_entry.update(data)

            elif sheet.category == 'ga' and sheet.sheet_type in (
                'ga_landing_pages', 'ga_other_sources'
            ):
                if not ga_integration:
                    report_entry['error'] = 'Google Analytics not connected'
                else:
                    data = _fetch_ga_report_data(ga_integration, sheet)
                    report_entry.update(data)

            elif sheet.sheet_type == 'ga_gsc_reconcile':
                if not ga_integration:
                    report_entry['error'] = 'Google Analytics not connected'
                elif not gsc_integration:
                    report_entry['error'] = 'Google Search Console not connected'
                else:
                    data = _fetch_ga_gsc_reconciliation_data(ga_integration, gsc_integration, sheet)
                    report_entry.update(data)

            elif sheet.sheet_type == 'keyword_ranking':
                # Route to weekly or monthly keyword ranking report
                if sheet.schedule == 'monthly':
                    data = _fetch_keyword_ranking_monthly(domain_id, sheet)
                else:
                    data = _fetch_keyword_ranking_weekly(domain_id, sheet)
                report_entry.update(data)

            elif sheet.sheet_type == 'domain_metrics':
                data = _fetch_domain_metrics_data(domain_id, sheet)
                report_entry.update(data)

            elif sheet.sheet_type == 'gsc_overview':
                if not gsc_integration:
                    report_entry['error'] = 'Google Search Console not connected'
                else:
                    data = _fetch_gsc_overview_data(gsc_integration, sheet)
                    report_entry.update(data)

            elif sheet.sheet_type == 'ga_overview':
                if not ga_integration:
                    report_entry['error'] = 'Google Analytics not connected'
                else:
                    data = _fetch_ga_overview_data(ga_integration, sheet)
                    report_entry.update(data)

            elif sheet.sheet_type == 'ga_organic_traffic_breakup':
                if not ga_integration:
                    report_entry['error'] = 'Google Analytics not connected'
                else:
                    data = _fetch_ga_organic_traffic_breakup_data(ga_integration, sheet)
                    report_entry.update(data)

            elif sheet.sheet_type == 'keyword_ranking_overview':
                data = _fetch_keyword_ranking_overview(domain_id, sheet)
                report_entry.update(data)

            else:
                report_entry['error'] = f'Unsupported report type: {sheet.sheet_type}'

        except Exception as e:
            logger.error(f"Error fetching data for sheet {sheet.id}: {e}")
            report_entry['error'] = str(e)

        reports.append(report_entry)

    return Response({'reports': reports, 'count': len(reports)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_report_export_xlsx(request):
    """
    Export all report sheets for a domain as a single .xlsx file.
    RankMax-style formatting: gold headers, green/red change values,
    metric group headers with merged cells.
    """
    from io import BytesIO
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter
    from django.http import HttpResponse
    from integrations.models import Integration

    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id required'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_ids = list(_get_user_domain_ids(request.user))
    if int(domain_id) not in allowed_ids:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    sheets = SeoReportSheet.objects.filter(
        domain_id=domain_id, is_active=True
    ).order_by('-created_at')

    if not sheets.exists():
        return Response({'error': 'No report sheets configured'}, status=status.HTTP_404_NOT_FOUND)

    gsc_integration = Integration.objects.filter(
        domain_id=domain_id, type='search_console', status='active'
    ).exclude(provider_id='').exclude(provider_id='pending_selection').exclude(provider_id__isnull=True).first()

    ga_integration = Integration.objects.filter(
        domain_id=domain_id, type='google_analytics', status='active'
    ).exclude(provider_id='').exclude(provider_id='pending_selection').exclude(provider_id__isnull=True).first()

    # ── Styles ────────────────────────────────────────────────────────────
    metric_header_fill = PatternFill(start_color="00B050", fill_type="solid")
    metric_header_font = Font(bold=True, color="FFFFFF", size=11)
    col_fill           = PatternFill(start_color="FFD966", fill_type="solid")
    col_font           = Font(bold=True, color="000000", size=10)
    change_col_fill    = PatternFill(start_color="FFFF00", fill_type="solid")
    change_col_font    = Font(bold=True, color="009E4F", size=10)
    pos_font           = Font(bold=True, color="009E4F")
    neg_font           = Font(bold=True, color="FF0000")
    center_align       = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left_align         = Alignment(horizontal='left', vertical='center')

    def _is_change_col(col_name):
        return ('Change' in col_name or 'MOM %' in col_name or 'YOY %' in col_name)

    def _is_dim_col(col_name):
        return col_name in ('Sr No', 'Metric', 'Pages', 'Queries', 'Landing Pages',
                            'Source', 'Keywords', 'Avg. Volume', 'Base Ranking')

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    for sheet in sheets:
        # ── Fetch data using the same dispatcher as seo_report_sheet_data ──
        data = {'columns': [], 'rows': [], 'error': None}
        try:
            if sheet.category == 'gsc' and sheet.sheet_type in (
                'gsc_pages', 'gsc_branded_queries', 'gsc_non_branded_queries', 'gsc_queries'
            ):
                if gsc_integration:
                    data = _fetch_gsc_report_data(gsc_integration, sheet)
            elif sheet.category == 'ga' and sheet.sheet_type in (
                'ga_landing_pages', 'ga_other_sources'
            ):
                if ga_integration:
                    data = _fetch_ga_report_data(ga_integration, sheet)
            elif sheet.sheet_type == 'ga_gsc_reconcile':
                if ga_integration and gsc_integration:
                    data = _fetch_ga_gsc_reconciliation_data(ga_integration, gsc_integration, sheet)
            elif sheet.sheet_type == 'keyword_ranking':
                if sheet.schedule == 'monthly':
                    data = _fetch_keyword_ranking_monthly(domain_id, sheet)
                else:
                    data = _fetch_keyword_ranking_weekly(domain_id, sheet)
            elif sheet.sheet_type == 'domain_metrics':
                data = _fetch_domain_metrics_data(domain_id, sheet)
            elif sheet.sheet_type == 'gsc_overview':
                if gsc_integration:
                    data = _fetch_gsc_overview_data(gsc_integration, sheet)
            elif sheet.sheet_type == 'ga_overview':
                if ga_integration:
                    data = _fetch_ga_overview_data(ga_integration, sheet)
            elif sheet.sheet_type == 'ga_organic_traffic_breakup':
                if ga_integration:
                    data = _fetch_ga_organic_traffic_breakup_data(ga_integration, sheet)
            elif sheet.sheet_type == 'keyword_ranking_overview':
                data = _fetch_keyword_ranking_overview(domain_id, sheet)
        except Exception as e:
            logger.error(f"Export: error fetching sheet {sheet.id}: {e}")
            data['error'] = str(e)

        columns = data.get('columns', [])
        rows    = data.get('rows', [])
        metrics_headers = data.get('metrics_headers', [])
        sub_tables      = data.get('tables') or []

        if not columns and not sub_tables:
            continue

        # ── Create worksheet ──────────────────────────────────────────────
        ws_title = sheet.sheet_name[:31]  # Excel sheet name max 31 chars
        ws = wb.create_sheet(title=ws_title)

        # ── Stacked sub-tables (e.g. GSC Overview: Clicks → Impressions →
        #    CTR, each with months down × Total/Branded/Non-Branded across) ──
        if sub_tables:
            from openpyxl.styles import Font as _Font
            bold_font = _Font(bold=True, color="000000")
            cur_row = 2
            for tbl in sub_tables:
                tcols  = tbl.get('columns', [])
                trows  = tbl.get('rows', [])
                ttitle = tbl.get('title', '')
                if not tcols:
                    continue
                ncols = len(tcols)

                # Title bar — merged across all columns of this sub-table
                title_cell = ws.cell(row=cur_row, column=1, value=ttitle.upper())
                title_cell.fill      = metric_header_fill
                title_cell.font      = metric_header_font
                title_cell.alignment = center_align
                if ncols > 1:
                    ws.merge_cells(
                        start_row=cur_row, start_column=1,
                        end_row=cur_row,   end_column=ncols
                    )
                    for fc in range(2, ncols + 1):
                        ws.cell(row=cur_row, column=fc).fill = metric_header_fill
                cur_row += 1

                # Column header row
                for ci, col_name in enumerate(tcols, 1):
                    cell = ws.cell(row=cur_row, column=ci, value=col_name)
                    cell.fill      = col_fill
                    cell.font      = col_font
                    cell.alignment = center_align
                cur_row += 1

                # Data rows
                for r in trows:
                    months_label  = str(r.get('Months', ''))
                    is_change_row = months_label in ('MOM %', 'WOW %', 'YOY %')
                    is_total_row  = months_label == 'Total'
                    is_pr_row     = '(PR)' in months_label
                    for ci, col_name in enumerate(tcols, 1):
                        val  = r.get(col_name, '')
                        cell = ws.cell(row=cur_row, column=ci, value=val)
                        if is_change_row and ci > 1:
                            try:
                                num = float(str(val).replace('%', '').replace('+', '').replace(',', ''))
                                if num > 0:
                                    cell.font = pos_font
                                elif num < 0:
                                    cell.font = neg_font
                            except (ValueError, TypeError):
                                pass
                        elif is_total_row or is_pr_row:
                            cell.font = bold_font
                        cell.alignment = left_align if col_name == 'Months' else center_align
                    cur_row += 1

                # Blank separator row before next sub-table
                cur_row += 1

            # Auto-size columns based on the widest cell across all sub-tables
            max_cols = max((len(t.get('columns', [])) for t in sub_tables), default=0)
            for ci in range(1, max_cols + 1):
                col_letter = get_column_letter(ci)
                max_len = 14
                for ri in range(2, cur_row):
                    cv = ws.cell(row=ri, column=ci).value
                    if cv is not None:
                        max_len = max(max_len, len(str(cv)))
                ws.column_dimensions[col_letter].width = min(max_len + 4, 40)

            # Done with this sheet — skip the legacy single-table render below
            continue

        # Row 1: empty (offset)
        data_start_row = 2

        # Row 2: metric group headers (merged) — if metrics_headers exist
        if metrics_headers:
            # Figure out which columns belong to each metric group
            col_idx = 1
            for c_name in columns:
                if _is_dim_col(c_name):
                    col_idx += 1
                else:
                    break
            metric_start = col_idx  # first metric column (1-based)

            cols_per_metric = 0
            if len(metrics_headers) > 0:
                non_dim_cols = [c for c in columns if not _is_dim_col(c)]
                cols_per_metric = len(non_dim_cols) // len(metrics_headers) if len(metrics_headers) > 0 else 0

            if cols_per_metric > 0:
                for mi, mh in enumerate(metrics_headers):
                    start_col = metric_start + mi * cols_per_metric
                    end_col   = start_col + cols_per_metric - 1
                    cell = ws.cell(row=2, column=start_col, value=mh.upper())
                    cell.fill = metric_header_fill
                    cell.font = metric_header_font
                    cell.alignment = center_align
                    if end_col > start_col:
                        ws.merge_cells(
                            start_row=2, start_column=start_col,
                            end_row=2, end_column=end_col
                        )
                        for fill_col in range(start_col + 1, end_col + 1):
                            ws.cell(row=2, column=fill_col).fill = metric_header_fill
                data_start_row = 3

        # Column headers row
        header_row = data_start_row
        for ci, col_name in enumerate(columns, 1):
            cell = ws.cell(row=header_row, column=ci, value=col_name)
            if _is_change_col(col_name):
                cell.fill = change_col_fill
                cell.font = change_col_font
            else:
                cell.fill = col_fill
                cell.font = col_font
            cell.alignment = center_align

        # Data rows
        for ri, row_data in enumerate(rows, header_row + 1):
            for ci, col_name in enumerate(columns, 1):
                val = row_data.get(col_name, '')
                cell = ws.cell(row=ri, column=ci, value=val)

                if _is_change_col(col_name):
                    # Parse numeric value for color
                    try:
                        num = float(str(val).replace('%', '').replace('+', '').replace(',', ''))
                        if num > 0:
                            cell.font = pos_font
                        elif num < 0:
                            cell.font = neg_font
                    except (ValueError, TypeError):
                        pass
                    cell.alignment = center_align
                elif _is_dim_col(col_name) and col_name != 'Sr No':
                    cell.alignment = left_align
                else:
                    cell.alignment = center_align

        # Auto-size columns
        for ci, col_name in enumerate(columns, 1):
            col_letter = get_column_letter(ci)
            max_len = len(str(col_name))
            for ri in range(header_row + 1, header_row + 1 + min(len(rows), 50)):
                cell_val = ws.cell(row=ri, column=ci).value
                if cell_val is not None:
                    max_len = max(max_len, len(str(cell_val)))
            ws.column_dimensions[col_letter].width = min(max_len + 4, 40)

    # ── Return the workbook ───────────────────────────────────────────────
    if len(wb.sheetnames) == 0:
        return Response({'error': 'No data to export'}, status=status.HTTP_404_NOT_FOUND)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    domain_name = sheets[0].domain.name if sheets else 'report'
    from datetime import datetime as _dt
    timestamp = _dt.now().strftime('%Y%m%d_%H%M%S')
    filename = f"seo-report-{domain_name.replace(' ', '_')}-{timestamp}.xlsx"

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ---------------------------------------------------------------------------
# Keyword Notes (CRUD) — mirrors RankMax kwNotes
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_keyword_notes_list(request, seo_kw_id):
    """List notes for a keyword."""
    allowed_ids = list(_get_user_domain_ids(request.user))

    try:
        seo_kw = SeoKeywordRank.objects.get(pk=seo_kw_id, domain_id__in=allowed_ids)
    except SeoKeywordRank.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    notes = SeoKeywordNote.objects.filter(seo_keyword_rank=seo_kw).select_related('created_by')
    serializer = SeoKeywordNoteSerializer(notes, many=True)

    # Also return a list of dates that have notes (for calendar highlighting)
    note_dates = list(notes.values_list('note_date', flat=True).distinct())

    return Response({
        'notes': serializer.data,
        'count': notes.count(),
        'note_dates': note_dates,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seo_keyword_note_create(request, seo_kw_id):
    """Create a note for a keyword."""
    allowed_ids = list(_get_user_domain_ids(request.user))

    try:
        seo_kw = SeoKeywordRank.objects.get(pk=seo_kw_id, domain_id__in=allowed_ids)
    except SeoKeywordRank.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = SeoKeywordNoteCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    note = SeoKeywordNote.objects.create(
        seo_keyword_rank=seo_kw,
        domain=seo_kw.domain,
        created_by=request.user,
        **serializer.validated_data,
    )
    return Response(SeoKeywordNoteSerializer(note).data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def seo_keyword_note_detail(request, seo_kw_id, note_id):
    """Update or delete a keyword note."""
    allowed_ids = list(_get_user_domain_ids(request.user))

    try:
        note = SeoKeywordNote.objects.select_related('seo_keyword_rank').get(
            pk=note_id,
            seo_keyword_rank_id=seo_kw_id,
            seo_keyword_rank__domain_id__in=allowed_ids,
        )
    except SeoKeywordNote.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        note.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PUT — update
    serializer = SeoKeywordNoteCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    note.title = serializer.validated_data['title']
    note.notes = serializer.validated_data['notes']
    note.note_date = serializer.validated_data['note_date']
    note.save()
    return Response(SeoKeywordNoteSerializer(note).data)


# ---------------------------------------------------------------------------
# Keyword Volume History — mirrors RankMax Volume History tab
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_keyword_volume(request, seo_kw_id):
    """Get volume history for a keyword."""
    allowed_ids = list(_get_user_domain_ids(request.user))

    try:
        seo_kw = SeoKeywordRank.objects.get(pk=seo_kw_id, domain_id__in=allowed_ids)
    except SeoKeywordRank.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        vol = SeoKeywordVolume.objects.get(seo_keyword_rank=seo_kw)
        return Response(SeoKeywordVolumeSerializer(vol).data)
    except SeoKeywordVolume.DoesNotExist:
        # Return empty/default volume data
        return Response({
            'id': None,
            'seo_keyword_rank': seo_kw_id,
            'average_volume': seo_kw.search_volume or 0,
            'top_volume': 0,
            'low_volume': 0,
            'comp_level': '-',
            'comp_index': '-',
            'month_wise_volume': [],
            'month_labels': [],
            'status': 'new',
        })


# ---------------------------------------------------------------------------
# Keyword Competitors — mirrors RankMax Competitors tab
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_keyword_competitors(request, seo_kw_id):
    """
    Get competitor domains for a specific keyword.
    Uses comp_today from SeoSerpFeatureHistory.
    Query params: type=tp (top 10, default), bf (before you), ar (after you)
    """
    allowed_ids = list(_get_user_domain_ids(request.user))

    try:
        seo_kw = SeoKeywordRank.objects.get(pk=seo_kw_id, domain_id__in=allowed_ids)
    except SeoKeywordRank.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    comp_type = request.query_params.get('type', 'tp')  # tp, bf, ar

    try:
        serp_history = SeoSerpFeatureHistory.objects.filter(
            seo_keyword_rank=seo_kw
        ).order_by('-modified_at').first()
    except SeoSerpFeatureHistory.DoesNotExist:
        serp_history = None

    competitors = []
    ads = []

    if serp_history:
        comp_today = serp_history.comp_today or {}
        competitors = comp_today.get(comp_type, [])

        # Get ad snippet data
        ad_history = serp_history.ad_snippet_history or {}
        ad_list = ad_history.get('list', {})
        ad_recent = ad_history.get('recent', [])

        for domain, ad_data in ad_list.items():
            ads.append({
                'domain': domain,
                'position': ad_data.get('ps', ''),
                'link': ad_data.get('lk', ''),
                'is_recent': domain in ad_recent,
            })

    return Response({
        'competitors': competitors,
        'ads': ads,
        'type': comp_type,
    })


# ---------------------------------------------------------------------------
# Force Reset & Re-scrape All Keywords
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seo_force_rescrape(request):
    """
    Force reset keywords to 'avail' and trigger scraping.

    Body:
        { "domain_id": 123 }   — single domain
        {}                     — all domains the user has access to

    Resets every status (busy, done, fail, load, read) back to 'avail'.

    Usage:
        # Single domain
        curl -X POST http://localhost:8000/api/seo/force-rescrape/ \
            -H "Authorization: Bearer <token>" \
            -H "Content-Type: application/json" \
            -d '{"domain_id": 123}'

        # All domains
        curl -X POST http://localhost:8000/api/seo/force-rescrape/ \
            -H "Authorization: Bearer <token>" \
            -H "Content-Type: application/json"
    """
    if request.user.role not in ['admin', 'super_admin']:
        return Response(
            {'error': 'Only admins can force re-scrape'},
            status=status.HTTP_403_FORBIDDEN,
        )

    import requests as http_requests
    engine_url = getattr(settings, 'ENGINE_API_URL', 'http://localhost:8001')
    allowed_ids = list(_get_user_domain_ids(request.user))

    domain_id = request.data.get('domain_id')

    # Build list of domains to process
    if domain_id:
        if int(domain_id) not in allowed_ids:
            return Response(
                {'error': 'Domain not found'},
                status=status.HTTP_403_FORBIDDEN,
            )
        target_domain_ids = [int(domain_id)]
    else:
        # All domains that have SEO keywords
        target_domain_ids = list(
            SeoKeywordRank.objects.filter(
                domain_id__in=allowed_ids,
            ).values_list('domain_id', flat=True).distinct()
        )

    if not target_domain_ids:
        return Response({
            'status': 'success',
            'message': 'No domains with SEO keywords found',
            'domains_processed': 0,
            'results': [],
        })

    results = []
    for did in target_domain_ids:
        total = SeoKeywordRank.objects.filter(domain_id=did).count()
        reset = SeoKeywordRank.objects.filter(
            domain_id=did,
        ).exclude(
            auto_call_status='avail',
        ).update(auto_call_status='avail')

        triggered = False
        try:
            resp = http_requests.post(
                f'{engine_url}/api/seo/process-domain/',
                json={'domain_id': did},
                timeout=10,
            )
            triggered = resp.status_code == 200
        except http_requests.RequestException:
            pass

        results.append({
            'domain_id': did,
            'total_keywords': total,
            'reset_count': reset,
            'triggered': triggered,
        })

        logger.info(
            f"[SEO Force Rescrape] Domain {did}: "
            f"reset {reset}/{total} keywords, triggered={triggered}"
        )

    total_kw = sum(r['total_keywords'] for r in results)
    return Response({
        'status': 'success',
        'message': f'Force re-scrape triggered for {total_kw} keywords across {len(results)} domain(s)',
        'domains_processed': len(results),
        'results': results,
    })
