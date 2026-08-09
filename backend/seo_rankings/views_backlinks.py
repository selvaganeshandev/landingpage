"""
Backlink profile — API views.

Org-scoped like the rest of seo_rankings (see views._get_user_domain_ids).
Nothing here calls DataForSEO; `POST /backlinks/fetch/` creates a snapshot and
hands it to the engine, and the page polls `GET /backlinks/` until the snapshot
reaches DONE.
"""
import csv
import logging

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from domains.models import Domain

from .models import SeoBacklinkItem
from .serializers_backlinks import (
    SeoBacklinkSnapshotSerializer,
    SeoBacklinkItemSerializer,
    SeoBacklinkReferringDomainSerializer,
    SeoBacklinkAnchorSerializer,
    SeoBacklinkPageSerializer,
    SeoBacklinkHistoryPointSerializer,
)
from .services import backlinks_service as svc
from .views import _get_user_domain_ids

logger = logging.getLogger(__name__)

# Rows per page in the backlinks table. The engine caps storage at 1,000 per
# snapshot, so this is about render cost, not fetch cost.
PAGE_SIZE = 50

SORTABLE = {
    'rank', 'domain_from_rank', 'page_from_rank', 'backlink_spam_score',
    'first_seen', 'last_seen', 'domain_from',
}


def _resolve_domain(request):
    """The domain the page is scoped to, or (None, error Response)."""
    domain_id = request.query_params.get('domain_id') or request.data.get('domain_id')
    if not domain_id:
        return None, Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    allowed = _get_user_domain_ids(request.user)
    domain = Domain.objects.filter(id=domain_id, id__in=allowed).first()
    if not domain:
        return None, Response({'error': 'Domain not found'}, status=status.HTTP_404_NOT_FOUND)
    return domain, None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def backlinks_overview(request):
    """Everything the page needs in one call.

    Returns `snapshot: null` when the project has never been fetched — that is
    the empty state with the "Fetch backlinks" button, not an error.
    """
    domain, err = _resolve_domain(request)
    if err:
        return err

    running = svc.running_snapshot(domain)
    snapshot = svc.latest_snapshot(domain)

    payload = {
        'domain_id': domain.id,
        'domain_name': domain.name,
        'domain_url': domain.url,
        'is_fetching': bool(running),
        'fetch_started_at': running.started_at if running else None,
        'snapshot': None,
        'history': [],
        'top_anchors': [],
        'top_referring_domains': [],
        'top_pages': [],
        'can_refresh': True,
        'next_refresh_allowed_at': None,
        'last_error': None,
    }

    if not snapshot:
        # Surface a failure from a never-successful project so the user sees
        # why the last press did nothing.
        failed = svc.last_failed_snapshot(domain)
        if failed and not running:
            payload['last_error'] = failed.error_message
        return Response(payload)

    payload['snapshot'] = SeoBacklinkSnapshotSerializer(snapshot).data
    payload['history'] = SeoBacklinkHistoryPointSerializer(
        snapshot.history_points.all(), many=True,
    ).data
    payload['top_anchors'] = SeoBacklinkAnchorSerializer(
        snapshot.anchor_rows.all()[:25], many=True,
    ).data
    payload['top_referring_domains'] = SeoBacklinkReferringDomainSerializer(
        snapshot.referring_domain_rows.all()[:25], many=True,
    ).data
    payload['top_pages'] = SeoBacklinkPageSerializer(
        snapshot.page_rows.all()[:25], many=True,
    ).data

    payload['next_refresh_allowed_at'] = snapshot.next_refresh_allowed_at
    try:
        svc.refresh_guard(domain)
    except svc.RefreshTooSoon:
        payload['can_refresh'] = False

    return Response(payload)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def backlinks_list(request):
    """The paginated, filterable backlinks table."""
    domain, err = _resolve_domain(request)
    if err:
        return err

    snapshot = svc.latest_snapshot(domain)
    if not snapshot:
        return Response({'count': 0, 'page': 1, 'page_size': PAGE_SIZE, 'results': []})

    qs = SeoBacklinkItem.objects.filter(snapshot=snapshot)

    search = (request.query_params.get('search') or '').strip()
    if search:
        from django.db.models import Q
        qs = qs.filter(
            Q(domain_from__icontains=search)
            | Q(anchor__icontains=search)
            | Q(url_from__icontains=search)
            | Q(url_to__icontains=search)
        )

    link_type = request.query_params.get('link_type')
    if link_type == 'dofollow':
        qs = qs.filter(dofollow=True)
    elif link_type == 'nofollow':
        qs = qs.filter(dofollow=False)

    for flag in ('is_new', 'is_lost', 'is_broken'):
        if request.query_params.get(flag) == 'true':
            qs = qs.filter(**{flag: True})

    sort = request.query_params.get('sort') or 'rank'
    direction = request.query_params.get('direction') or 'desc'
    if sort not in SORTABLE:
        sort = 'rank'
    qs = qs.order_by(f"{'-' if direction == 'desc' else ''}{sort}")

    total = qs.count()
    try:
        page = max(1, int(request.query_params.get('page') or 1))
    except ValueError:
        page = 1
    start = (page - 1) * PAGE_SIZE

    return Response({
        'count': total,
        'page': page,
        'page_size': PAGE_SIZE,
        'total_backlinks': snapshot.backlinks,
        'is_truncated': snapshot.is_truncated,
        'results': SeoBacklinkItemSerializer(qs[start:start + PAGE_SIZE], many=True).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def backlinks_fetch(request):
    """Start a pull. 429 when inside the monthly window, 409 when one is running.

    The 429 body carries `next_refresh_allowed_at` — the alert the UI shows
    quotes that date verbatim rather than recomputing it.
    """
    domain, err = _resolve_domain(request)
    if err:
        return err

    try:
        snapshot = svc.start_fetch(domain, account=request.user)
    except svc.RefreshTooSoon as exc:
        return Response(
            {
                'error': str(exc),
                'next_refresh_allowed_at': exc.next_allowed_at,
                'code': 'refresh_too_soon',
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    except svc.FetchAlreadyRunning as exc:
        return Response(
            {
                'error': str(exc),
                'snapshot_id': exc.snapshot.id,
                'code': 'already_running',
            },
            status=status.HTTP_409_CONFLICT,
        )
    except Exception as exc:
        logger.exception("[BL] Could not start fetch for domain %s", domain.pk)
        return Response({'error': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    return Response(
        {'snapshot_id': snapshot.id, 'status': snapshot.status},
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def backlinks_export(request):
    """CSV of every stored backlink for the latest snapshot.

    Streams the whole snapshot, not the current page — an export that honoured
    pagination would silently hand back 50 of 1,000 rows.
    """
    domain, err = _resolve_domain(request)
    if err:
        return err

    snapshot = svc.latest_snapshot(domain)
    if not snapshot:
        return Response({'error': 'No backlink data to export'}, status=status.HTTP_404_NOT_FOUND)

    host = (domain.url or domain.name or 'project').replace('https://', '').replace('http://', '').strip('/')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="backlinks-{host}-{snapshot.completed_at:%Y-%m-%d}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([
        'Source domain', 'Source URL', 'Target URL', 'Anchor', 'Link type',
        'Follow', 'Domain rank', 'Page rank', 'Link rank', 'Spam score',
        'Country', 'Placement', 'New', 'Lost', 'Broken',
        'First seen', 'Last seen', 'Source page title',
    ])
    rows = SeoBacklinkItem.objects.filter(snapshot=snapshot).order_by('-rank').iterator(chunk_size=500)
    for r in rows:
        writer.writerow([
            r.domain_from, r.url_from, r.url_to, r.anchor, r.item_type,
            'dofollow' if r.dofollow else 'nofollow',
            r.domain_from_rank, r.page_from_rank, r.rank, r.backlink_spam_score,
            r.domain_from_country, r.semantic_location,
            'yes' if r.is_new else '', 'yes' if r.is_lost else '',
            'yes' if r.is_broken else '',
            r.first_seen.date() if r.first_seen else '',
            r.last_seen.date() if r.last_seen else '',
            r.page_from_title,
        ])
    return response
