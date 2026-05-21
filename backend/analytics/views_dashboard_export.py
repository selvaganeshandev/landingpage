"""
Excel export for the Insights (Dashboard) page.

Produces an .xlsx matching the "AI Visibility" reference template:
  Block 1: per-LLM mentions for your brand + each competitor + totals row.
  Block 2: per-LLM page citations + total cited pages.
  Block 3: Backlink Portfolio — placeholders (not tracked per competitor here).

This module is intentionally standalone — it reuses the same models/querysets
as dashboard_summary but does not import or call it, so existing behavior is
untouched.
"""

from datetime import datetime, timedelta
from io import BytesIO

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from analytics.models import ShareOfVoiceAnalytics
from competitors.models import Competitor
from domains.models import Domain
from prompts.models import PromptGroupMetricSnapshot


# Order in which LLM platforms appear in the exported report.
# Matches the Insights page LLM dropdown exactly so the export always lists
# every supported LLM (with 0 for platforms that have no data this period).
# Labels here are the values stored on snapshot/SOV rows in the DB.
LLM_PLATFORM_ORDER = [
    "ChatGPT",
    "Google Gemini",
    "Perplexity",
    "Claude",
    "Grok",
    "DeepSeek",
]

VISIBILITY_DEFINITION = (
    "AI Visibility score measures how often the brand appears in AI-generated "
    "answers across major LLM platforms."
)
MENTIONS_DEFINITION = (
    "The total number of prompts that trigger AI responses mentioning your brand."
)
CITATIONS_DEFINITION = "No. of times pages were citated on each LLM Platforms "
LLM_CITED_TIMES_DEFINITION = "No. of times brand was citated on each LLM Platforms "
TOTAL_CITED_PAGES_DEFINITION = "Your domain's pages cited in AI-generated answers."


def _period_types_for_query(days: int):
    if days < 30:
        return ["daily", "weekly", "monthly"]
    if days <= 90:
        return ["weekly", "daily", "monthly"]
    return ["monthly", "weekly", "daily"]


def _normalize_platform_filter(llm_model):
    if not llm_model or llm_model == "all":
        return None
    mapping = {
        "chatgpt": "ChatGPT",
        "claude": "Claude",
        "gemini": "Google Gemini",
        "perplexity": "Perplexity",
        "grok": "Grok",
        "deepseek": "DeepSeek",
    }
    return mapping.get(llm_model.lower(), llm_model.capitalize())


def _domain_display_name(domain):
    """Mirror the frontend Dashboard label: capitalize first letter, leave rest intact."""
    raw = (domain.name or "").strip()
    if not raw:
        return "Your Brand"
    return raw[0].upper() + raw[1:]


def _build_brand_columns(domain, sov_latest_rows):
    """Return ordered list: [{'name': <domain>, ...}, <competitors by market_position>]."""
    your_brand_url = domain.url or domain.name or ""
    brands = [{
        "name": _domain_display_name(domain),
        "url": your_brand_url,
        "competitor_id": None,
    }]

    competitor_rows = (
        sov_latest_rows.filter(competitor__isnull=False)
        .exclude(competitor_id=None)
        .order_by("market_position")
    )
    seen = set()
    for row in competitor_rows:
        cid = row.competitor_id
        if cid in seen:
            continue
        seen.add(cid)
        try:
            comp = Competitor.objects.get(id=cid)
        except Competitor.DoesNotExist:
            continue
        brands.append({"name": comp.name, "url": comp.url, "competitor_id": cid})
    return brands


def _platforms_for_report(sov_latest_rows):
    """Always return the full canonical LLM list (matching the Insights LLM dropdown).
    Any extra platforms found in the data that aren't in the canonical list are
    appended at the end, alphabetically. Platforms with no data get 0 cells."""
    ordered = list(LLM_PLATFORM_ORDER)
    found = set(
        sov_latest_rows.exclude(platform__isnull=True)
        .exclude(platform="")
        .values_list("platform", flat=True)
        .distinct()
    )
    extras = sorted(p for p in found if p not in LLM_PLATFORM_ORDER)
    return ordered + extras


def _mention_matrix(sov_latest_rows, brands, platforms):
    """Build {(competitor_id_or_None, platform_label): mention_count}."""
    matrix = {}
    for row in sov_latest_rows.exclude(platform__isnull=True).exclude(platform=""):
        key = (row.competitor_id, row.platform)
        matrix[key] = (matrix.get(key) or 0) + (row.mention_count or 0)
    return matrix


def _brand_totals(sov_latest_rows, brands):
    """Aggregate row (platform IS NULL) per brand → total mentions."""
    totals = {}
    for row in sov_latest_rows.filter(platform__isnull=True):
        totals[row.competitor_id] = row.mention_count or 0
    # Fallback: if aggregate row missing for some brand, sum its platform rows.
    for b in brands:
        if b["competitor_id"] not in totals:
            totals[b["competitor_id"]] = sum(
                (row.mention_count or 0)
                for row in sov_latest_rows.filter(
                    competitor_id=b["competitor_id"]
                ).exclude(platform__isnull=True).exclude(platform="")
            )
    return totals


def _brand_visibility(sov_latest_rows, brands):
    """share_percentage of the aggregate (platform IS NULL) row per brand, 0-100."""
    vis = {}
    for row in sov_latest_rows.filter(platform__isnull=True):
        vis[row.competitor_id] = float(row.share_percentage or 0)
    for b in brands:
        vis.setdefault(b["competitor_id"], 0.0)
    return vis


def _your_brand_llm_citations(domain_id, start_date, end_date):
    """
    Per-LLM citation totals for *your* domain only, from PromptGroupMetricSnapshot.
    Competitor citations aren't tracked per-platform in this app, so the
    competitor columns in Block 2 get blank/N/A.
    """
    qs = PromptGroupMetricSnapshot.objects.filter(
        prompt_group__domain_id=domain_id,
        snapshot_date__gte=start_date,
        snapshot_date__lte=end_date,
    ).exclude(platform__isnull=True).exclude(platform="")

    totals = {}
    for snap in qs:
        platform = snap.platform
        totals[platform] = totals.get(platform, 0) + int(snap.citations or 0)
    return totals


def _write_header_label(ws, cell_ref, value, *, bold=True, fill=None):
    cell = ws[cell_ref]
    cell.value = value
    if bold:
        cell.font = Font(bold=True)
    if fill:
        cell.fill = PatternFill("solid", fgColor=fill)
    cell.alignment = Alignment(vertical="center", wrap_text=True)


def _build_workbook(domain, brands, platforms, mention_matrix, brand_totals,
                    brand_visibility, your_llm_citations):
    wb = Workbook()
    ws = wb.active
    ws.title = "AI Visibility"

    # Column widths
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 60
    for i, _ in enumerate(brands):
        col_letter = ws.cell(row=1, column=4 + i).column_letter
        ws.column_dimensions[col_letter].width = 16

    HEADER_FILL = "F2F2F2"
    BLOCK_FILL = "E8E8FF"

    # ---------- Block 1 ----------
    _write_header_label(ws, "B1", "Pillars", fill=BLOCK_FILL)
    _write_header_label(ws, "C1", "URL", fill=BLOCK_FILL)

    _write_header_label(ws, "C2", "Defination", fill=HEADER_FILL)
    for i, b in enumerate(brands):
        _write_header_label(ws, ws.cell(row=2, column=4 + i).coordinate, b["name"],
                            fill=HEADER_FILL)

    # Row 3: AI Visibility Score
    ws["B3"] = "AI Visibility Score"
    ws["B3"].font = Font(bold=True)
    ws["C3"] = VISIBILITY_DEFINITION
    ws["C3"].alignment = Alignment(wrap_text=True, vertical="center")
    for i, b in enumerate(brands):
        score = brand_visibility.get(b["competitor_id"], 0.0)
        ws.cell(row=3, column=4 + i, value=f"{int(round(score))}/100")

    # Rows 4..N: per-LLM mentions
    row = 4
    for idx, platform in enumerate(platforms):
        ws.cell(row=row, column=2, value=platform).font = Font(bold=True)
        if idx == 0:
            ws.cell(row=row, column=3, value=LLM_CITED_TIMES_DEFINITION)
            ws.cell(row=row, column=3).alignment = Alignment(wrap_text=True, vertical="center")
        for i, b in enumerate(brands):
            count = mention_matrix.get((b["competitor_id"], platform), 0)
            ws.cell(row=row, column=4 + i, value=int(count))
        row += 1

    # Mentions total row
    ws.cell(row=row, column=2, value="Mentions").font = Font(bold=True)
    ws.cell(row=row, column=3, value=MENTIONS_DEFINITION)
    ws.cell(row=row, column=3).alignment = Alignment(wrap_text=True, vertical="center")
    for i, b in enumerate(brands):
        total = brand_totals.get(b["competitor_id"], 0)
        if total == 0:
            # Fallback: sum the per-platform cells for that column
            total = sum(
                mention_matrix.get((b["competitor_id"], p), 0) for p in platforms
            )
        ws.cell(row=row, column=4 + i, value=int(total))
    row += 1

    # Rows for Referring Domains / Total Backlinks / Pages Indexed in SERP — N/A
    for label in ("Number of Referring Domains", "Number of Total Backlinks",
                  "Pages Indexed in SERP"):
        ws.cell(row=row, column=2, value=label).font = Font(bold=True)
        for i, _ in enumerate(brands):
            ws.cell(row=row, column=4 + i, value="N/A")
        row += 1

    # ---------- Block 2 ----------
    row += 1  # blank spacer row
    _write_header_label(ws, ws.cell(row=row, column=2).coordinate,
                        "AI Citations - Pages", fill=BLOCK_FILL)
    _write_header_label(ws, ws.cell(row=row, column=3).coordinate,
                        "Defination", fill=BLOCK_FILL)
    for i, b in enumerate(brands):
        _write_header_label(ws, ws.cell(row=row, column=4 + i).coordinate,
                            b["name"], fill=BLOCK_FILL)
    row += 1

    # Per-LLM citation counts (your brand only — others get blank)
    for idx, platform in enumerate(platforms):
        ws.cell(row=row, column=2, value=platform).font = Font(bold=True)
        if idx == 0:
            ws.cell(row=row, column=3, value=CITATIONS_DEFINITION)
            ws.cell(row=row, column=3).alignment = Alignment(wrap_text=True, vertical="center")
        ws.cell(row=row, column=4, value=int(your_llm_citations.get(platform, 0)))
        for i in range(1, len(brands)):
            ws.cell(row=row, column=4 + i, value="N/A")
        row += 1

    # Total Cited Pages row
    ws.cell(row=row, column=2, value="Total Cited Pages").font = Font(bold=True)
    ws.cell(row=row, column=3, value=TOTAL_CITED_PAGES_DEFINITION)
    ws.cell(row=row, column=3).alignment = Alignment(wrap_text=True, vertical="center")
    ws.cell(row=row, column=4, value=int(sum(your_llm_citations.values())))
    for i in range(1, len(brands)):
        ws.cell(row=row, column=4 + i, value="N/A")
    row += 1

    # ---------- Block 3: Backlink Portfolio (placeholders) ----------
    row += 1
    _write_header_label(ws, ws.cell(row=row, column=3).coordinate,
                        "Backlink Portfolio", fill=BLOCK_FILL)
    for i, b in enumerate(brands):
        _write_header_label(ws, ws.cell(row=row, column=4 + i).coordinate,
                            b["name"], fill=BLOCK_FILL)
    row += 1
    for label in ("Referring Domains", "CAT A", "CAT B", "CAT C",
                  "Number of Total Backlinks", "CAT A", "CAT B", "CAT C"):
        ws.cell(row=row, column=3, value=label)
        for i, _ in enumerate(brands):
            ws.cell(row=row, column=4 + i, value="N/A")
        row += 1

    return wb


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_export(request):
    """
    GET /analytics/dashboard/export/?domain_id=...&days=30&llm_model=all

    Streams an .xlsx file matching the AI Visibility report template.
    """
    domain_id = request.query_params.get("domain_id")
    if not domain_id:
        return Response({"error": "domain_id is required"},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        days = int(request.query_params.get("days", 30))
    except (TypeError, ValueError):
        days = 30

    platform_filter = _normalize_platform_filter(request.query_params.get("llm_model"))
    domain = get_object_or_404(Domain, id=domain_id)

    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days - 1)

    sov_qs = ShareOfVoiceAnalytics.objects.filter(
        domain_id=domain_id,
        timestamp__gte=start_date,
        timestamp__lte=end_date,
    )
    if platform_filter:
        sov_qs = sov_qs.filter(platform=platform_filter)

    if sov_qs.exists():
        latest_day = sov_qs.order_by("-timestamp").first().timestamp
        latest_rows = sov_qs.filter(timestamp=latest_day)
    else:
        latest_rows = sov_qs.none()

    brands = _build_brand_columns(domain, latest_rows)
    platforms = _platforms_for_report(latest_rows)
    if platform_filter:
        # Honor the LLM dropdown: only include the selected platform's row.
        platforms = [platform_filter]

    matrix = _mention_matrix(latest_rows, brands, platforms)
    totals = _brand_totals(latest_rows, brands)
    visibility = _brand_visibility(latest_rows, brands)
    your_citations = _your_brand_llm_citations(domain_id, start_date, end_date)

    wb = _build_workbook(domain, brands, platforms, matrix, totals, visibility,
                         your_citations)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    safe_name = (domain.name or f"domain-{domain_id}").replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"{safe_name}_AI_Visibility_{timestamp}.xlsx"

    response = HttpResponse(
        buf.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
