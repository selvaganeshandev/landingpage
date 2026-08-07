"""
SEO Rankings — insight views built from data already collected.

Read-only endpoints. Org-scoped via request.user.organisation → Domain access,
using the same _get_user_domain_ids helper as views.py.
"""
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .views import _get_user_domain_ids
from .services.opportunities_service import build_opportunities

logger = logging.getLogger(__name__)

MAX_LIMIT = 500


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_opportunities(request):
    """
    Keywords worth working on, bucketed by how close they are to earning clicks.
    Query params: domain_id (required), platform (default desktop), limit (default 50)
    """
    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        domain_id = int(domain_id)
    except (TypeError, ValueError):
        return Response({'error': 'domain_id must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

    if domain_id not in list(_get_user_domain_ids(request.user)):
        return Response({'error': 'Domain not found or access denied'}, status=status.HTTP_403_FORBIDDEN)

    platform = request.query_params.get('platform', 'desktop')

    # No limit by default: the page receives every scored keyword and paginates
    # client-side. `limit` stays available for callers that want a top-N.
    raw_limit = request.query_params.get('limit')
    limit = None
    if raw_limit:
        try:
            limit = max(1, min(int(raw_limit), MAX_LIMIT))
        except (TypeError, ValueError):
            limit = None

    return Response(build_opportunities(domain_id, platform=platform, limit=limit))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_share_of_voice(request):
    """
    Volume-weighted visibility share for us and every rival domain seen in our
    tracked results pages.
    Query params: domain_id (required), platform (default desktop), top (default 25)
    """
    from .services.share_of_voice_service import build_share_of_voice, DEFAULT_TOP_N

    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        domain_id = int(domain_id)
    except (TypeError, ValueError):
        return Response({'error': 'domain_id must be an integer'}, status=status.HTTP_400_BAD_REQUEST)
    if domain_id not in list(_get_user_domain_ids(request.user)):
        return Response({'error': 'Domain not found or access denied'}, status=status.HTTP_403_FORBIDDEN)

    try:
        top_n = max(1, min(int(request.query_params.get('top', DEFAULT_TOP_N)), 200))
    except (TypeError, ValueError):
        top_n = DEFAULT_TOP_N

    return Response(build_share_of_voice(
        domain_id,
        platform=request.query_params.get('platform', 'desktop'),
        top_n=top_n,
    ))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_opportunity_detail(request, seo_kw_id):
    """
    One opportunity, expanded: score breakdown, recommended action, and every
    other tracked keyword ranking through the same URL.
    """
    from .services.opportunities_service import build_opportunity_detail

    detail = build_opportunity_detail(seo_kw_id, _get_user_domain_ids(request.user))
    if detail is None:
        return Response(
            {'error': 'Keyword not found or access denied'},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(detail)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seo_opportunities_export(request):
    """
    Export the three opportunity classifications as a single .xlsx workbook,
    one sheet each plus a Notes sheet explaining the derived figures.
    Query params: domain_id (required), platform (default desktop)
    """
    from django.http import HttpResponse
    from domains.models import Domain
    from .services.opportunities_export import build_opportunities_workbook

    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        domain_id = int(domain_id)
    except (TypeError, ValueError):
        return Response({'error': 'domain_id must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

    if domain_id not in list(_get_user_domain_ids(request.user)):
        return Response({'error': 'Domain not found or access denied'}, status=status.HTTP_403_FORBIDDEN)

    platform = request.query_params.get('platform', 'desktop')
    domain = Domain.objects.filter(id=domain_id).first()
    label = getattr(domain, 'name', None) or getattr(domain, 'url', '') or str(domain_id)

    stream, _ = build_opportunities_workbook(domain_id, label, platform=platform)

    response = HttpResponse(
        stream.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="opportunities.xlsx"'
    return response
