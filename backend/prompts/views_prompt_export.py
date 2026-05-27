"""
Excel export for the Prompts (Prompt Monitoring) page.

Produces an .xlsx with a single "AI Prompt Data Export" sheet — one row per
(prompt × platform) analytics record, matching the reference template.

Isolated module: imports the PromptAnalytics queryset directly. No changes to
existing views/endpoints — the existing mentions export keeps working.
"""

from datetime import datetime
from io import BytesIO
from urllib.parse import urlparse

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from domains.models import Domain
from .models import PromptAnalytics


# Match the reference template column headers exactly.
COLUMN_HEADERS = [
    "Source URLs",
    "Prompt Text",
    "Model",
    "Avg Sentiment",
    "Avg Position",
    "Mentions",
    "Created",
]

# Display labels for the Model column. The DB stores some long-form names
# ("Google Gemini") — shorten for readability while keeping the rest intact.
PLATFORM_DISPLAY = {
    "Google Gemini": "Gemini",
    "Bard": "Gemini",
}


def _extract_domain(url: str) -> str:
    """Return the bare domain (e.g. 'example.com') from a URL. Falls back
    to the raw URL fragment if parsing fails."""
    if not url or not isinstance(url, str):
        return ""
    try:
        parsed = urlparse(url if "://" in url else f"http://{url}")
        netloc = parsed.netloc or parsed.path
        netloc = netloc.split("/")[0].strip()
        return netloc
    except Exception:
        return url.strip()


def _format_source_urls(citation_list) -> str:
    """Reference format: comma-separated domains, or 'No sources available'.
    Kept for backward-compat with consumers that expect the legacy string."""
    if not citation_list or not isinstance(citation_list, list):
        return "No sources available"
    domains, seen = [], set()
    for item in citation_list:
        url = item if isinstance(item, str) else (item.get("url") if isinstance(item, dict) else None)
        d = _extract_domain(url or "")
        if d and d.lower() not in seen:
            seen.add(d.lower())
            domains.append(d)
    return ", ".join(domains) if domains else "No sources available"


def _group_urls_by_domain(citation_list):
    """Group full citation URLs under their parent domain so the UI can show
    each subpage that was actually cited. Returns a list of
    ``{"domain": str, "urls": [str, ...]}`` entries in first-seen order."""
    if not citation_list or not isinstance(citation_list, list):
        return []
    grouped = {}
    order = []
    for item in citation_list:
        url = item if isinstance(item, str) else (item.get("url") if isinstance(item, dict) else None)
        if not url or not isinstance(url, str):
            continue
        full = url.strip()
        if not full:
            continue
        domain = _extract_domain(full)
        if not domain:
            continue
        key = domain.lower()
        if key not in grouped:
            grouped[key] = {"domain": domain, "urls": []}
            order.append(key)
        if full not in grouped[key]["urls"]:
            grouped[key]["urls"].append(full)
    return [grouped[k] for k in order]


def _format_source_urls_full(citation_list) -> str:
    """Newline-separated full URLs grouped by domain, for the Excel cell.
    Falls back to 'No sources available' when nothing is present."""
    groups = _group_urls_by_domain(citation_list)
    if not groups:
        return "No sources available"
    lines = []
    for g in groups:
        lines.append(g["domain"])
        for u in g["urls"]:
            lines.append(f"  - {u}")
    return "\n".join(lines)


def _display_platform(platform: str) -> str:
    if not platform:
        return ""
    return PLATFORM_DISPLAY.get(platform, platform)


def _scale_sentiment(score) -> float:
    """sentiment_score is stored -1.00..1.00; reference shows 0..100. Map: (s+1)*50."""
    try:
        return round((float(score or 0) + 1.0) * 50.0, 1)
    except (TypeError, ValueError):
        return 0.0


def _apply_date_range(qs, request):
    """Filter ``qs`` by optional ``start_date``/``end_date`` (YYYY-MM-DD)
    query params on ``created_at``. Returns ``(qs, error_response_or_None)``."""
    start_param = request.query_params.get("start_date")
    end_param = request.query_params.get("end_date")
    if not start_param and not end_param:
        return qs, None
    try:
        start_date = datetime.strptime(start_param, "%Y-%m-%d").date() if start_param else None
        end_date = datetime.strptime(end_param, "%Y-%m-%d").date() if end_param else None
    except ValueError:
        return qs, Response(
            {"error": "start_date and end_date must be YYYY-MM-DD"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if start_date and end_date and start_date > end_date:
        return qs, Response(
            {"error": "start_date cannot be after end_date"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)
    return qs, None


def _format_created(dt) -> str:
    """Reference format: '5/16/2026, 8:32:04 AM' (no leading zeros on M/D/H)."""
    if not dt:
        return ""
    # %-m / %-d / %-I aren't portable — strip zero padding manually.
    s = dt.strftime("%m/%d/%Y, %I:%M:%S %p")
    parts = s.split(", ")
    date_parts = parts[0].split("/")
    date_parts = [p.lstrip("0") or "0" for p in date_parts]
    time_parts = parts[1].split(":")
    time_parts[0] = time_parts[0].lstrip("0") or "0"
    return f"{'/'.join(date_parts)}, {':'.join(time_parts)}"


def _build_workbook(rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "AI Prompt Data Export"

    header_fill = PatternFill("solid", fgColor="F2F2F2")
    header_font = Font(bold=True)
    for col_idx, label in enumerate(COLUMN_HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center")

    for r_idx, row in enumerate(rows, start=2):
        for c_idx, value in enumerate(row, start=1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            if c_idx in (1, 2):  # Source URLs, Prompt Text
                cell.alignment = Alignment(wrap_text=True, vertical="top")

    column_widths = {1: 60, 2: 50, 3: 14, 4: 14, 5: 14, 6: 12, 7: 22}
    for col, width in column_widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.freeze_panes = "A2"
    return wb


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def prompts_export(request):
    """
    GET /prompts/export/?domain_id=...

    Streams an .xlsx file with one row per (prompt × platform) analytics record
    for the given domain.
    """
    domain_id = request.query_params.get("domain_id")
    if not domain_id:
        return Response({"error": "domain_id is required"},
                        status=status.HTTP_400_BAD_REQUEST)

    domain = get_object_or_404(Domain, id=domain_id)

    qs = (
        PromptAnalytics.objects
        .filter(prompt__group__domain_id=domain_id, is_published=True)
        .select_related("prompt", "prompt__group")
        .order_by("-created_at")
    )
    qs, range_err = _apply_date_range(qs, request)
    if range_err is not None:
        return range_err

    rows = []
    for a in qs.iterator():
        prompt_text = a.prompt.prompt if a.prompt else ""
        rows.append((
            _format_source_urls_full(a.citation_list),
            prompt_text,
            _display_platform(a.platform),
            _scale_sentiment(a.sentiment_score),
            float(a.position or 0),
            int(a.total_mentions or 0),
            _format_created(a.created_at),
        ))

    wb = _build_workbook(rows)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    safe_name = (domain.name or f"domain-{domain_id}").replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"{safe_name}_AI_Prompt_Data_Export_{timestamp}.xlsx"

    response = HttpResponse(
        buf.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def prompts_export_data(request):
    """
    GET /prompts/export/data/?domain_id=...

    JSON sibling of prompts_export — same row shape and formatting helpers, so
    the on-screen Sources page shows exactly what the .xlsx download contains.
    """
    domain_id = request.query_params.get("domain_id")
    if not domain_id:
        return Response(
            {"error": "domain_id is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    domain = get_object_or_404(Domain, id=domain_id)

    qs = (
        PromptAnalytics.objects
        .filter(prompt__group__domain_id=domain_id, is_published=True)
        .select_related("prompt", "prompt__group")
        .order_by("-created_at")
    )
    qs, range_err = _apply_date_range(qs, request)
    if range_err is not None:
        return range_err

    rows = []
    for a in qs.iterator():
        prompt_text = a.prompt.prompt if a.prompt else ""
        rows.append({
            "source_urls": _format_source_urls(a.citation_list),
            "source_url_groups": _group_urls_by_domain(a.citation_list),
            "prompt_text": prompt_text,
            "model": _display_platform(a.platform),
            "avg_sentiment": _scale_sentiment(a.sentiment_score),
            "avg_position": float(a.position or 0),
            "mentions": int(a.total_mentions or 0),
            "created": _format_created(a.created_at),
        })

    return Response({
        "domain_id": int(domain_id),
        "domain_name": domain.name,
        "columns": COLUMN_HEADERS,
        "rows": rows,
        "total_rows": len(rows),
    })
