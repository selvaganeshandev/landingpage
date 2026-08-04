"""
Billing endpoints — per-project keyword charges, split by region.

Super-admin only, enforced here as well as on the tab, so the data is
unreachable by URL for anyone else (BILLING_KEYWORD_CALCULATION.md §5.1).

Price is computed server-side by services/billing.py and sent pre-computed;
the client sums the rows it receives and does no pricing arithmetic.
"""
import logging
from io import BytesIO

from django.conf import settings
from django.db.models import Count
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from domains.models import Domain
from .models import SeoKeywordRank
from .services.billing import (
    CURRENCY,
    PLANS,
    REGIONS,
    build_row,
    region_key_for,
    summarise,
)

logger = logging.getLogger(__name__)


def _is_super_admin(user) -> bool:
    return getattr(user, "role", None) == "super_admin"


def _can_view_all_orgs(user) -> bool:
    """Whether this account may see every organisation's charges.

    Driven by BILLING_ALL_ORG_EMAILS so the list is config, not code. Everyone
    else — including other super admins — stays scoped to their own
    organisation.
    """
    allowed = {
        e.strip().lower()
        for e in (getattr(settings, "BILLING_ALL_ORG_EMAILS", "") or "").split(",")
        if e.strip()
    }
    return (getattr(user, "email", "") or "").lower() in allowed


def _visible_organisations(user):
    """Organisations this account may report on, as [{id, name}]."""
    from domains.models import Domain

    if not _can_view_all_orgs(user):
        org = user.organisation
        return [{"id": org.id, "name": org.name}] if org else []

    rows = (
        Domain.objects.values("organisation_id", "organisation__name")
        .distinct()
        .order_by("organisation__name")
    )
    return [
        {"id": r["organisation_id"], "name": r["organisation__name"] or f"Org {r['organisation_id']}"}
        for r in rows
        if r["organisation_id"]
    ]


def _resolve_scope(request):
    """Work out which organisations this request covers.

    Returns (can_view_all, organisations, selected, org_ids) or None when the
    requested organisation is not one the caller may see. Shared by the summary
    and the export so the two can never report on different scopes.
    """
    user = request.user
    can_view_all = _can_view_all_orgs(user)
    organisations = _visible_organisations(user)

    # ?organisation=all | <id>. Anyone without the all-orgs grant is pinned to
    # their own organisation regardless of what they ask for.
    requested = (request.query_params.get("organisation") or "").strip().lower()
    if not can_view_all:
        return can_view_all, [], "own", None
    if requested and requested != "all":
        try:
            wanted = int(requested)
        except ValueError:
            return None
        if wanted not in {o["id"] for o in organisations}:
            return None
        return can_view_all, organisations, str(wanted), [wanted]

    # Consolidated is the default for an all-orgs viewer — the point of the
    # grant is seeing everything at once.
    return can_view_all, organisations, "all", [o["id"] for o in organisations]


def _billing_regions(user, organisation_ids=None):
    """Build the region tables for the requesting user's organisation.

    Every domain in the organisation appears, including those tracking no
    keywords yet — the rate card is priced "per project", so a project costs
    the entry slab whether or not keywords have been added. Scoping is by
    organisation, so each super admin sees only their own account.

    Counts come from one annotated query rather than a count per domain.
    """
    domains = Domain.objects.annotate(used=Count("seo_keyword_ranks"))
    if organisation_ids is None:
        domains = domains.filter(organisation=user.organisation)
    else:
        domains = domains.filter(organisation_id__in=organisation_ids)
    domains = domains.select_related("organisation").order_by("-used", "name")

    buckets = {r["key"]: [] for r in REGIONS}
    for d in domains:
        row = build_row(
            domain_id=d.id,
            name=d.name,
            url=d.url,
            country=d.country,
            used_keywords=d.used,
        )
        # Carried so a consolidated view can say which account a project is
        # under; ignored when viewing a single organisation.
        row.organisation = d.organisation.name if d.organisation else ""
        buckets.setdefault(region_key_for(row.country), []).append(row)

    return [
        {
            "key": region["key"],
            "label": region["label"],
            "projects": [r.as_dict() for r in buckets.get(region["key"], [])],
            **summarise(buckets.get(region["key"], [])),
        }
        for region in REGIONS
    ]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def billing_summary(request):
    """Per-project billing rows grouped into region tables."""
    if not _is_super_admin(request.user):
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    scope = _resolve_scope(request)
    if scope is None:
        return Response({"error": "Invalid organisation"}, status=status.HTTP_400_BAD_REQUEST)
    can_view_all, organisations, selected, org_ids = scope

    regions = _billing_regions(request.user, organisation_ids=org_ids)
    return Response({
        "currency": CURRENCY,
        "rate_card": PLANS,
        "regions": regions,
        # Across every region, so the header figure does not depend on which
        # table you happen to be looking at.
        "grand_total": sum(r["total_price"] for r in regions),
        "total_projects": sum(r["total_projects"] for r in regions),
        "can_view_all_orgs": can_view_all,
        # Export covers one organisation's account; it is not offered in the
        # consolidated view, where "the account" is ambiguous.
        "can_export": not can_view_all,
        "organisations": organisations if can_view_all else [],
        "selected_organisation": selected,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def billing_export(request):
    """XLSX of every region — the whole account, not the visible table."""
    if not _is_super_admin(request.user):
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    scope = _resolve_scope(request)
    if scope is None:
        return Response({"error": "Invalid organisation"}, status=status.HTTP_400_BAD_REQUEST)
    _can_view_all, _orgs, _selected, org_ids = scope

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    regions = _billing_regions(request.user, organisation_ids=org_ids)

    wb = Workbook()
    wb.remove(wb.active)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="6D28D9")
    total_font = Font(bold=True)

    for region in regions:
        # Excel forbids / \ ? * [ ] : in sheet names and caps them at 31 chars.
        title = region["label"].replace("&", "and")[:31]
        ws = wb.create_sheet(title=title)

        multi_org = len({p["organisation"] for p in region["projects"]}) > 1
        headers = ["#", "Project", "Domain", "Country"]
        if multi_org:
            headers.append("Organisation")
        headers += ["Used Keywords", "Keyword Limit", f"Price ({CURRENCY})"]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        for i, p in enumerate(region["projects"], start=1):
            row = [i, p["name"], p["url"], p["country"]]
            if multi_org:
                row.append(p["organisation"])
            row += [p["used_keywords"], p["keyword_limit"], p["price"]]
            ws.append(row)

        ws.append([])
        total_row = ws.max_row + 1
        price_col = len(headers)
        ws.cell(row=total_row, column=1, value=f"Total — {region['billable_projects']} billable of {region['total_projects']} project(s)").font = total_font
        ws.cell(row=total_row, column=price_col, value=region["total_price"]).font = total_font

        widths = [6, 32, 40, 22] + ([26] if multi_org else []) + [16, 16, 16]
        for idx, width in enumerate(widths, start=1):
            ws.column_dimensions[chr(64 + idx)].width = width

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    response = HttpResponse(
        buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="promptmaxx_billing.xlsx"'
    return response
