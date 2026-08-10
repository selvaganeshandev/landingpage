"""
SEO content gap — API views.

Distinct from `competitors.content_gap_analysis`, which answers a different
question: that one is GEO, comparing which brands the LLMs mention. This one is
organic search — which competitor pages outrank us on keywords we track.

Org-scoped like the rest of seo_rankings (see views._get_user_domain_ids).
Reads only; nothing here writes or spends.
"""
import logging

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from domains.models import Domain

from .models import SeoKeywordRank
from .services.content_gap_export import build_content_gap_workbook
from .services.content_gap_service import build_content_gaps, gap_detail, summarise
from .views import _get_user_domain_ids

logger = logging.getLogger(__name__)

# Rows per page. The analysis runs over every tracked keyword regardless — the
# summary counts and the bucket totals must reflect the whole project, not the
# slice on screen — so this caps rendering only.
PAGE_SIZE = 50


def _resolve_domain(request):
    domain_id = request.query_params.get("domain_id")
    if not domain_id:
        return None, Response({"error": "domain_id is required"},
                              status=status.HTTP_400_BAD_REQUEST)
    allowed = _get_user_domain_ids(request.user)
    domain = Domain.objects.filter(id=domain_id, id__in=allowed).first()
    if not domain:
        return None, Response({"error": "Domain not found"},
                              status=status.HTTP_404_NOT_FOUND)
    return domain, None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def seo_content_gaps(request):
    """Gap rows plus a summary for one project.

    Filters (`bucket`, `intent`, `content_type`, `action`, `search`) are applied
    after the analysis, so the summary always describes the whole project while
    the rows narrow. A filtered view that also shrank the headline numbers would
    make the page contradict itself.
    """
    domain, err = _resolve_domain(request)
    if err:
        return err

    platform = request.query_params.get("platform")
    rows, no_serp = build_content_gaps(domain, platform=platform)

    total_tracked = SeoKeywordRank.objects.filter(domain=domain).count()
    summary = summarise(rows, no_serp, total_tracked)

    for key in ("bucket", "intent", "content_type", "action"):
        value = request.query_params.get(key)
        if value and value != "all":
            rows = [r for r in rows if r[key] == value]

    search = (request.query_params.get("search") or "").strip().lower()
    if search:
        rows = [r for r in rows
                if search in r["keyword"].lower()
                or search in r["leader"]["domain"].lower()]

    total = len(rows)
    try:
        page = max(1, int(request.query_params.get("page") or 1))
    except ValueError:
        page = 1
    start = (page - 1) * PAGE_SIZE

    return Response({
        "domain_id": domain.id,
        "domain_name": domain.name,
        "summary": summary,
        "count": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "results": rows[start:start + PAGE_SIZE],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def seo_content_gaps_export(request):
    """Workbook of every gap: Summary first, then the rows and the breakdowns.

    Exports the whole project, not the page on screen — an export that honoured
    pagination would hand back 50 of several hundred rows, which is the kind of
    quiet truncation that gets acted on. The summary leads because the row list
    alone cannot say how much of the project was analysable.
    """
    domain, err = _resolve_domain(request)
    if err:
        return err

    platform = request.query_params.get("platform")
    rows, no_serp = build_content_gaps(domain, platform=platform)
    total_tracked = SeoKeywordRank.objects.filter(domain=domain).count()
    summary = summarise(rows, no_serp, total_tracked)

    host = (domain.url or domain.name or "project").replace("https://", "") \
        .replace("http://", "").strip("/")
    stream = build_content_gap_workbook(
        rows, summary, domain.name or host,
        platform_label=(platform or "All").title(),
    )

    response = HttpResponse(
        stream.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="seo-content-gaps-{host}.xlsx"'
    )
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def seo_content_gap_detail(request, seo_kw_id):
    """One gap keyword in full: the whole results page, our rank history, and
    the evidence for and against treating it as a gap.

    Returns 404 rather than an empty case when the keyword is not a gap — a
    detail page that argues for a keyword the list would never show would be
    manufacturing a recommendation.
    """
    allowed = _get_user_domain_ids(request.user)
    seo_kw = (SeoKeywordRank.objects
              .filter(id=seo_kw_id, domain_id__in=allowed)
              .select_related("keyword", "domain")
              .first())
    if not seo_kw:
        return Response({"error": "Keyword not found"},
                        status=status.HTTP_404_NOT_FOUND)

    detail = gap_detail(seo_kw)
    if detail is None:
        return Response(
            {"error": "This keyword is not a content gap",
             "reason": "It has no stored results page, or you already hold a "
                       "page-one position for it."},
            status=status.HTTP_404_NOT_FOUND)

    detail["domain_id"] = seo_kw.domain_id
    detail["domain_name"] = seo_kw.domain.name
    detail["domain_url"] = seo_kw.domain.url
    return Response(detail)
