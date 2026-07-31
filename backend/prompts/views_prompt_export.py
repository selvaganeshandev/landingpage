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
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.queryset_scoping import user_can_access_domain
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


# Order the per-platform sheets appear in, and the order their columns appear
# in on Summary. Fixed rather than derived from the data so the workbook has
# the same shape for every domain and two exports can be diffed.
PLATFORM_SHEETS = ["ChatGPT", "Claude", "Google Gemini", "Perplexity", "Grok", "DeepSeek"]

SUMMARY_HEADERS_HEAD = [
    "Prompt", "Theme", "Platforms tracked", "Mentioned on",
    "Total Mentions", "Total Citations", "Best Position", "Avg Sentiment",
]

PLATFORM_HEADERS = [
    "Prompt", "Theme", "Mentioned", "Position", "Mentions", "Citations",
    "Sentiment", "Sentiment Score", "Competitors Mentioned", "Topics",
    "Source URLs", "Tracked",
]

_HEADER_FILL = PatternFill("solid", fgColor="F2F2F2")
_WRAP = Alignment(wrap_text=True, vertical="top")


def _citation_count(rec):
    """Number of sources cited in this answer.

    Counted from citation_list rather than the total_citations column, because
    that column is populated for some domains and left at 0 for others — Tata
    Motors carries 0 on all 400 of its rows while 219 of them have a non-empty
    citation_list. Counting the list is the only measure that works everywhere,
    and it agrees with the Source URLs cell beside it.
    """
    cl = rec.citation_list
    return len(cl) if isinstance(cl, list) else 0


def _write_sheet(ws, headers, rows, widths, wrap_cols=()):
    for col_idx, label in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.font = Font(bold=True)
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(vertical="center")

    for r_idx, row in enumerate(rows, start=2):
        for c_idx, value in enumerate(row, start=1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            if c_idx in wrap_cols:
                cell.alignment = _WRAP

    for col, width in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.freeze_panes = "A2"


def _build_workbook(by_prompt, platforms_present):
    """Summary sheet + one sheet per platform.

    The old export was a single flat sheet of (prompt x platform) rows, which
    made the obvious research question — how does one prompt rank across the
    models? — a manual pivot. Summary answers it directly with a Position
    column per platform; the per-platform sheets carry the detail (citations,
    sources, competitors) that only makes sense scoped to one model.
    """
    wb = Workbook()

    # Only ship a column/sheet for platforms this domain actually has, but keep
    # PLATFORM_SHEETS' order so the layout is stable across domains.
    ordered = [p for p in PLATFORM_SHEETS if p in platforms_present]
    ordered += sorted(p for p in platforms_present if p not in PLATFORM_SHEETS)

    # ---- Summary ----
    ws = wb.active
    ws.title = "Summary"
    headers = SUMMARY_HEADERS_HEAD + [f"Position — {_display_platform(p)}" for p in ordered]

    summary_rows = []
    for entry in by_prompt:
        recs = entry["records"]
        positions = [float(r.position or 0) for r in recs if (r.position or 0) > 0]
        sentiments = [_scale_sentiment(r.sentiment_score) for r in recs]
        mentioned_on = [_display_platform(r.platform) for r in recs if r.is_mention]
        row = [
            entry["prompt_text"],
            entry["theme"],
            len(recs),
            ", ".join(mentioned_on),
            sum(int(r.total_mentions or 0) for r in recs),
            sum(_citation_count(r) for r in recs),
            # Lower is better, so "best" is the minimum of the ranks that exist.
            # 0 means "not ranked" rather than "ranked first", so it is excluded
            # above — averaging it in would flatter every unranked prompt.
            min(positions) if positions else "",
            round(sum(sentiments) / len(sentiments), 2) if sentiments else "",
        ]
        for platform in ordered:
            rec = entry["by_platform"].get(platform)
            row.append(float(rec.position or 0) if rec and (rec.position or 0) > 0 else "")
        summary_rows.append(row)

    widths = {1: 60, 2: 24, 3: 16, 4: 30, 5: 14, 6: 14, 7: 13, 8: 13}
    for i in range(len(ordered)):
        widths[len(SUMMARY_HEADERS_HEAD) + 1 + i] = 20
    _write_sheet(ws, headers, summary_rows, widths, wrap_cols=(1,))

    # ---- One sheet per platform ----
    for platform in ordered:
        rows = []
        for entry in by_prompt:
            rec = entry["by_platform"].get(platform)
            if not rec:
                continue
            rows.append([
                entry["prompt_text"],
                entry["theme"],
                "Yes" if rec.is_mention else "No",
                float(rec.position or 0) if (rec.position or 0) > 0 else "",
                int(rec.total_mentions or 0),
                _citation_count(rec),
                rec.sentiment_category or "",
                _scale_sentiment(rec.sentiment_score),
                ", ".join(str(c) for c in (rec.competitor_mention_list or [])),
                ", ".join(str(t) for t in (rec.topic_list or [])),
                _format_source_urls_full(rec.citation_list),
                _format_created(rec.tracked_at or rec.created_at),
            ])
        # Excel caps sheet titles at 31 chars and forbids []:*?/\ — the display
        # names in use are short and clean, but truncate defensively.
        sheet = wb.create_sheet(_display_platform(platform)[:31])
        _write_sheet(
            sheet, PLATFORM_HEADERS, rows,
            {1: 60, 2: 22, 3: 11, 4: 10, 5: 10, 6: 10, 7: 13, 8: 15,
             9: 34, 10: 30, 11: 70, 12: 22},
            wrap_cols=(1, 9, 10, 11),
        )

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

    # Group by prompt so Summary can put one prompt on a row with a column per
    # platform. Keeping only the LATEST record per (prompt, platform): analytics
    # rows are updated in place on each run, but a re-run can leave more than
    # one, and two rows for the same pair would otherwise double the totals.
    by_prompt = []
    index = {}
    platforms_present = set()
    for a in qs.iterator():
        if not a.prompt:
            continue
        platforms_present.add(a.platform)
        key = a.prompt_id
        entry = index.get(key)
        if entry is None:
            entry = {
                "prompt_text": a.prompt.prompt or "",
                "theme": getattr(a.prompt.group, "theme", "") or "",
                "records": [],
                "by_platform": {},
            }
            index[key] = entry
            by_prompt.append(entry)
        # qs is ordered -created_at, so the first record seen for a platform is
        # the most recent one; later duplicates are older and dropped.
        if a.platform not in entry["by_platform"]:
            entry["by_platform"][a.platform] = a
            entry["records"].append(a)

    by_prompt.sort(key=lambda e: e["prompt_text"].lower())

    wb = _build_workbook(by_prompt, platforms_present)
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


# ---------------------------------------------------------------------------
# Single prompt group export
#
# The domain-wide export answers "how is this domain doing across its prompts".
# Researching ONE prompt is a different question — which model ranks it where,
# what each actually said, and which sources it leaned on — and pulling that out
# of a 100-row workbook meant filtering by hand. This scopes the same shape to
# one group and adds the answer text, which is the thing worth reading when the
# question is about a single prompt.
# ---------------------------------------------------------------------------

GROUP_VARIANT_HEADERS_HEAD = ["Variant"]


def _latest_by_prompt_platform(group):
    """{prompt_id: {platform: latest PromptAnalytics}} for a group.

    Latest-per-pair, matching what the detail page shows: analytics rows are
    rewritten in place each run, but a re-run can leave more than one, and
    summing them would count a single LLM answer more than once.
    """
    rows = (
        PromptAnalytics.objects
        .filter(prompt__group=group, is_published=True)
        .exclude(platform__isnull=True).exclude(platform="")
        .select_related("prompt")
        .order_by("-created_at")
    )
    latest = {}
    for a in rows:
        per_prompt = latest.setdefault(a.prompt_id, {})
        if a.platform not in per_prompt:
            per_prompt[a.platform] = a
    return latest


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def prompt_group_export(request, group_id):
    """GET /prompts/groups/<id>/export/ — one workbook for a single prompt group."""
    from .models import PromptGroup  # local: avoids a circular import at module load

    group = get_object_or_404(
        PromptGroup.objects.select_related("domain"), id=group_id
    )
    if not user_can_access_domain(request.user, group.domain_id, request):
        return Response({"error": "Prompt group not found"},
                        status=status.HTTP_404_NOT_FOUND)

    latest = _latest_by_prompt_platform(group)
    prompts = list(group.prompts.all())
    platforms_present = {p for per in latest.values() for p in per}
    ordered = [p for p in PLATFORM_SHEETS if p in platforms_present]
    ordered += sorted(p for p in platforms_present if p not in PLATFORM_SHEETS)

    wb = Workbook()

    # ---- Overview ----
    ws = wb.active
    ws.title = "Overview"
    totals = {p: 0 for p in ordered}
    for per in latest.values():
        for platform, rec in per.items():
            totals[platform] = totals.get(platform, 0) + int(rec.total_mentions or 0)

    overview = [
        ["Domain", group.domain.name or ""],
        ["Prompt group", group.id],
        ["Theme", group.theme or ""],
        ["Variants tracked", len(prompts)],
        ["Total Mentions (all LLMs)", sum(totals.values())],
        ["Visibility Score", float(group.visibility_score or 0)],
        ["Exported", _format_created(timezone.now())],
        [],
        ["Mentions by platform", ""],
    ]
    for platform in ordered:
        overview.append([_display_platform(platform), totals.get(platform, 0)])
    _write_sheet(ws, ["Field", "Value"], overview, {1: 34, 2: 60}, wrap_cols=(2,))

    # ---- Variants: one row per variant, a column pair per platform ----
    headers = list(GROUP_VARIANT_HEADERS_HEAD)
    for platform in ordered:
        label = _display_platform(platform)
        headers += [f"Mentions — {label}", f"Position — {label}"]

    variant_rows = []
    for prompt in prompts:
        per = latest.get(prompt.id, {})
        row = [prompt.prompt or ""]
        for platform in ordered:
            rec = per.get(platform)
            row.append(int(rec.total_mentions or 0) if rec else "")
            # 0 means "not ranked", not "ranked first" — blank rather than
            # printing a value that reads as the best possible result.
            row.append(float(rec.position or 0) if rec and (rec.position or 0) > 0 else "")
        variant_rows.append(row)

    widths = {1: 70}
    for i in range(len(ordered) * 2):
        widths[2 + i] = 18
    _write_sheet(wb.create_sheet("Variants"), headers, variant_rows, widths, wrap_cols=(1,))

    # ---- One sheet per platform ----
    for platform in ordered:
        rows = []
        for prompt in prompts:
            rec = latest.get(prompt.id, {}).get(platform)
            if not rec:
                continue
            rows.append([
                prompt.prompt or "",
                group.theme or "",
                "Yes" if rec.is_mention else "No",
                float(rec.position or 0) if (rec.position or 0) > 0 else "",
                int(rec.total_mentions or 0),
                _citation_count(rec),
                rec.sentiment_category or "",
                _scale_sentiment(rec.sentiment_score),
                ", ".join(str(c) for c in (rec.competitor_mention_list or [])),
                ", ".join(str(t) for t in (rec.topic_list or [])),
                _format_source_urls_full(rec.citation_list),
                _format_created(rec.tracked_at or rec.created_at),
            ])
        _write_sheet(
            wb.create_sheet(_display_platform(platform)[:31]),
            PLATFORM_HEADERS, rows,
            {1: 60, 2: 22, 3: 11, 4: 10, 5: 10, 6: 10, 7: 13, 8: 15,
             9: 34, 10: 30, 11: 70, 12: 22},
            wrap_cols=(1, 9, 10, 11),
        )

    # ---- Responses: the answers themselves ----
    # The reason to export a single prompt is usually to read what each model
    # actually said, which no other sheet carries.
    response_rows = []
    for prompt in prompts:
        per = latest.get(prompt.id, {})
        for platform in ordered:
            rec = per.get(platform)
            if not rec or not (rec.context_summary or "").strip():
                continue
            response_rows.append([
                prompt.prompt or "",
                _display_platform(platform),
                _format_created(rec.tracked_at or rec.created_at),
                rec.context_summary,
            ])
    _write_sheet(
        wb.create_sheet("Responses"), ["Variant", "Platform", "Tracked", "Full AI Response"],
        response_rows, {1: 50, 2: 16, 3: 22, 4: 130}, wrap_cols=(1, 4),
    )

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    safe_domain = (group.domain.name or "domain").replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"{safe_domain}_Prompt_{group.id}_{timestamp}.xlsx"

    response = HttpResponse(
        buf.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
