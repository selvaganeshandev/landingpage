"""
Excel export for the Insights (Dashboard) page.

Produces an .xlsx matching the "AI Visibility" reference template:
  Block 1: per-LLM mentions for your brand + each competitor + totals row.
  Block 2: per-LLM page citations + total cited pages.
  Block 3: Backlink Portfolio — referring domains, total backlinks and CAT A/B/C
           breakdown fetched live from DataForSEO (primary) / Moz (fallback) for
           your brand and each competitor URL.

Sheets 2..n ("Summary", "Trend", "By Platform", "Cited Pages", "Mentions",
"By Country", "AI Traffic", "Definitions") cover the domain's own performance,
which the competitor grid above says nothing about. Those are built from
dashboard_summary's response rather than from re-derived queries, so the
workbook cannot drift from the page it was exported from.
"""

import base64
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from io import BytesIO
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.db.models.functions import Coalesce

from analytics.models import ShareOfVoiceAnalytics
from analytics.views_dashboard import (
    _canonical_page,
    _citation_entry_url,
    _dashboard_datetime_window,
    _url_host,
    dashboard_summary,
)
from competitors.models import Competitor
from domains.models import Domain
from core.queryset_scoping import user_can_access_domain
from integrations.models import GAAITrafficDaily
from prompts.models import PromptAnalytics, PromptGroupMetricSnapshot

logger = logging.getLogger(__name__)


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


def _hidden_platforms():
    """LLMs whose rows are suppressed from the export.
    Returns a set for fast membership checks. Empty set = show every platform.
    """
    return set(getattr(settings, "AI_VISIBILITY_HIDDEN_PLATFORMS", []) or [])


def _platforms_for_report(sov_latest_rows):
    """Return the canonical LLM list minus any platforms hidden via settings.
    Any extra platforms found in the data that aren't in the canonical list are
    appended at the end, alphabetically (also filtered against the hide-list).
    Platforms with no data still get 0 cells.
    """
    hidden = _hidden_platforms()
    ordered = [p for p in LLM_PLATFORM_ORDER if p not in hidden]
    found = set(
        sov_latest_rows.exclude(platform__isnull=True)
        .exclude(platform="")
        .values_list("platform", flat=True)
        .distinct()
    )
    extras = sorted(p for p in found if p not in LLM_PLATFORM_ORDER and p not in hidden)
    return ordered + extras


def _mention_matrix(sov_period_rows, brands, platforms):
    """Build {(competitor_id_or_None, platform_label): mention_count} —
    summed across every snapshot day in the selected period (Q1b)."""
    matrix = {}
    for row in sov_period_rows.exclude(platform__isnull=True).exclude(platform=""):
        key = (row.competitor_id, row.platform)
        matrix[key] = (matrix.get(key) or 0) + (row.mention_count or 0)
    return matrix


def _brand_totals(sov_period_rows, brands):
    """Total mentions per brand across the period — summed from per-platform
    rows so we never under-count when the daily aggregate row is missing for
    some days. Hidden platforms (AI_VISIBILITY_HIDDEN_PLATFORMS) are skipped so
    the Mentions total stays consistent with the visible per-LLM rows.
    """
    hidden = _hidden_platforms()
    totals = {b["competitor_id"]: 0 for b in brands}
    qs = sov_period_rows.exclude(platform__isnull=True).exclude(platform="")
    if hidden:
        qs = qs.exclude(platform__in=hidden)
    for row in qs:
        if row.competitor_id in totals:
            totals[row.competitor_id] = totals.get(row.competitor_id, 0) + (row.mention_count or 0)
    return totals


def _brand_visibility(sov_latest_rows, brands):
    """share_percentage of the aggregate (platform IS NULL) row per brand on
    the latest snapshot day, 0-100. Visibility is a "current state" metric,
    not a sum, so we intentionally keep this on the latest day even though
    mentions are now period-summed."""
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

    # Drop hidden LLMs so the Total Cited Pages row equals the sum of the
    # visible per-LLM rows (otherwise the total appears inflated to the reader).
    hidden = _hidden_platforms()
    if hidden:
        qs = qs.exclude(platform__in=hidden)

    totals = {}
    for snap in qs:
        platform = snap.platform
        totals[platform] = totals.get(platform, 0) + int(snap.citations or 0)
    return totals


# ---------------------------------------------------------------------------
# Backlink Portfolio — dynamic providers
# ---------------------------------------------------------------------------
# Block 3 of the AI Visibility export used to render hard-coded "N/A" for every
# brand. The helpers below fetch real numbers per-brand from the first provider
# that is configured (DataForSEO preferred — broader index — then Moz as a
# fallback because it's already wired up in the project). Pages Indexed in SERP
# comes from a Scrapingdog `site:` query. If no provider is configured, the
# corresponding cell stays "N/A" — same behaviour as before for self-hosted
# installs without API keys, so nothing else in the system is impacted.

_BACKLINK_EMPTY = {
    "referring_domains": None,
    "total_backlinks": None,
    "cat_a_domains": None,
    "cat_b_domains": None,
    "cat_c_domains": None,
    "cat_a_backlinks": None,
    "cat_b_backlinks": None,
    "cat_c_backlinks": None,
    "pages_indexed": None,
}


def _root_domain(url):
    """Return bare host (no scheme/path) from a URL or already-bare host string."""
    if not url:
        return ""
    raw = url.strip()
    if "://" not in raw:
        raw = "http://" + raw
    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower()
    return host[4:] if host.startswith("www.") else host


def _classify_by_da(da):
    """Moz Domain Authority (0-100) → CAT A/B/C — mirrors domains/views.py thresholds."""
    if da is None:
        return None
    if da >= 70:
        return "A"
    if da >= 40:
        return "B"
    return "C"


def _classify_by_rank(rank):
    """DataForSEO rank (0-1000) → CAT A/B/C using the same 70 / 40 cutoffs scaled ×10."""
    if rank is None:
        return None
    if rank >= 700:
        return "A"
    if rank >= 400:
        return "B"
    return "C"


def _fetch_dataforseo_backlinks(host):
    login = getattr(settings, "DATAFORSEO_LOGIN", None)
    password = getattr(settings, "DATAFORSEO_PASSWORD", None)
    if not login or not password or not host:
        return None

    use_sandbox = bool(getattr(settings, "DATAFORSEO_USE_SANDBOX", False))
    base_url = "https://sandbox.dataforseo.com" if use_sandbox else "https://api.dataforseo.com"
    if use_sandbox:
        # Sandbox returns the same fixture for every target — log once per call
        # so the source of the numbers is obvious in dev logs.
        logger.warning(
            "DataForSEO sandbox mode active for %s — numbers are mock data, not real backlinks.",
            host,
        )

    try:
        token = base64.b64encode(f"{login}:{password}".encode("utf-8")).decode("utf-8")
        headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}

        s_resp = requests.post(
            f"{base_url}/v3/backlinks/summary/live",
            headers=headers,
            json=[{
                "target": host,
                "internal_list_limit": 10,
                "backlinks_status_type": "live",
            }],
            timeout=20,
        )
        if s_resp.status_code != 200:
            logger.warning(
                "DataForSEO summary returned %s for %s: %s",
                s_resp.status_code, host, s_resp.text[:200],
            )
            return None
        s_payload = s_resp.json() or {}
        tasks = s_payload.get("tasks") or []
        summary_results = (tasks[0].get("result") if tasks else None) or []
        summary = summary_results[0] if summary_results else {}
        ref_domains = int(summary.get("referring_domains") or 0)
        total_backlinks = int(summary.get("backlinks") or 0)

        cat_domains = {"A": 0, "B": 0, "C": 0}
        cat_backlinks = {"A": 0, "B": 0, "C": 0}

        d_resp = requests.post(
            f"{base_url}/v3/backlinks/referring_domains/live",
            headers=headers,
            json=[{
                "target": host,
                "limit": 1000,
                "order_by": ["rank,desc"],
                "backlinks_status_type": "live",
            }],
            timeout=30,
        )
        if d_resp.status_code == 200:
            d_payload = d_resp.json() or {}
            d_tasks = d_payload.get("tasks") or []
            d_results = (d_tasks[0].get("result") if d_tasks else None) or []
            items = (d_results[0].get("items") if d_results else None) or []
            for entry in items:
                cat = _classify_by_rank(entry.get("rank"))
                if not cat:
                    continue
                cat_domains[cat] += 1
                cat_backlinks[cat] += int(entry.get("backlinks") or 0)
        else:
            logger.warning(
                "DataForSEO referring_domains returned %s for %s: %s",
                d_resp.status_code, host, d_resp.text[:200],
            )

        return {
            "referring_domains": ref_domains,
            "total_backlinks": total_backlinks,
            "cat_a_domains": cat_domains["A"],
            "cat_b_domains": cat_domains["B"],
            "cat_c_domains": cat_domains["C"],
            "cat_a_backlinks": cat_backlinks["A"],
            "cat_b_backlinks": cat_backlinks["B"],
            "cat_c_backlinks": cat_backlinks["C"],
            "pages_indexed": None,
        }
    except Exception as exc:
        logger.warning("DataForSEO backlink fetch failed for %s: %s", host, exc)
        return None


def _fetch_moz_backlinks(host):
    """Fallback to Moz when DataForSEO isn't configured.
    Re-uses the Moz helpers already defined in domains.views so we don't fork the
    auth/parsing logic. Import is local so the export module doesn't take a hard
    dependency on the domains app at import time.
    """
    if not host:
        return None
    try:
        from domains.views import _fetch_moz_url_metrics, _fetch_moz_links
    except Exception as exc:
        logger.warning("Could not import Moz helpers: %s", exc)
        return None

    target = f"https://{host}"
    metrics = _fetch_moz_url_metrics(target)
    if metrics is None:
        return None

    links = _fetch_moz_links(target, limit=50) or []
    cat_domains = {"A": set(), "B": set(), "C": set()}
    cat_backlinks = {"A": 0, "B": 0, "C": 0}
    for link in links:
        cat = _classify_by_da(link.get("source_domain_authority") or 0)
        if not cat:
            continue
        src_domain = link.get("source_root_domain") or ""
        if src_domain:
            cat_domains[cat].add(src_domain)
        cat_backlinks[cat] += 1

    return {
        "referring_domains": int(metrics.get("linking_root_domains") or 0),
        "total_backlinks": int(metrics.get("external_links") or 0),
        "cat_a_domains": len(cat_domains["A"]),
        "cat_b_domains": len(cat_domains["B"]),
        "cat_c_domains": len(cat_domains["C"]),
        "cat_a_backlinks": cat_backlinks["A"],
        "cat_b_backlinks": cat_backlinks["B"],
        "cat_c_backlinks": cat_backlinks["C"],
        "pages_indexed": None,
    }


def _fetch_pages_indexed_dataforseo(host):
    """Google's `About N results` count for `site:host` via DataForSEO SERP API.
    Returns se_results_count (~$0.01 per call from prepaid balance).

    Note: SERP always uses the live api.dataforseo.com endpoint, even when
    DATAFORSEO_USE_SANDBOX=True. SERP is pay-per-call from the prepaid balance,
    so there's no reason to fall back to mock data — and sandbox returns a
    fixed fixture per query, not useful real-world numbers. The sandbox toggle
    only gates Backlinks (which require a separate paid subscription).
    """
    login = getattr(settings, "DATAFORSEO_LOGIN", None)
    password = getattr(settings, "DATAFORSEO_PASSWORD", None)
    if not login or not password or not host:
        return None

    try:
        token = base64.b64encode(f"{login}:{password}".encode("utf-8")).decode("utf-8")
        resp = requests.post(
            "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
            headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"},
            json=[{
                "keyword": f"site:{host}",
                "location_code": 2840,
                "language_code": "en",
                "depth": 10,
            }],
            timeout=30,
        )
        if resp.status_code != 200:
            logger.warning(
                "DataForSEO SERP returned %s for site:%s: %s",
                resp.status_code, host, resp.text[:200],
            )
            return None
        payload = resp.json() or {}
        tasks = payload.get("tasks") or []
        result = (tasks[0].get("result") if tasks else None) or []
        if result:
            count = result[0].get("se_results_count")
            if count is not None:
                return int(count)
    except Exception as exc:
        logger.warning("DataForSEO pages-indexed fetch failed for %s: %s", host, exc)
    return None


def _fetch_pages_indexed_scrapingdog(host):
    """Fallback pages-indexed via Scrapingdog's dedicated /google API.
    The legacy /scrape endpoint no longer handles Google searches (returns a
    redirect-message JSON). The /google endpoint returns structured search
    results at 5 credits per request.
    """
    api_key = getattr(settings, "SCRAPINGDOG_API_KEY", None)
    if not api_key or not host:
        return None
    try:
        resp = requests.get(
            "https://api.scrapingdog.com/google",
            params={"api_key": api_key, "query": f"site:{host}"},
            timeout=20,
        )
        if resp.status_code != 200:
            return None
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        # Scrapingdog returns a `success: false` body with HTTP 200 when out
        # of credits — treat that as a soft failure.
        if isinstance(data, dict) and data.get("success") is False:
            logger.warning(
                "Scrapingdog soft failure for site:%s: %s",
                host, (data.get("message") or "")[:200],
            )
            return None
        # Try common fields where Scrapingdog reports the total-results count.
        for key in ("total_results", "search_information", "search_metadata"):
            val = data.get(key) if isinstance(data, dict) else None
            if isinstance(val, dict):
                for sub in ("total_results", "result_count", "approximate_results", "results_count"):
                    if val.get(sub) is not None:
                        return int(str(val[sub]).replace(",", ""))
            elif val is not None:
                return int(str(val).replace(",", ""))
    except Exception as exc:
        logger.warning("Scrapingdog pages-indexed fetch failed for %s: %s", host, exc)
    return None


def _fetch_pages_indexed(host):
    """Return Google's `site:<host>` indexed-pages count.
    Tries DataForSEO SERP first (pay-per-call from prepaid balance), then
    Scrapingdog. Returns None if both providers fail / are unconfigured.
    """
    return (
        _fetch_pages_indexed_dataforseo(host)
        or _fetch_pages_indexed_scrapingdog(host)
    )


def _fetch_brand_backlinks(brand):
    host = _root_domain(brand.get("url"))
    if not host:
        return _BACKLINK_EMPTY.copy()
    data = _fetch_dataforseo_backlinks(host) or _fetch_moz_backlinks(host)
    if data is None:
        data = _BACKLINK_EMPTY.copy()
    if data.get("pages_indexed") is None:
        data["pages_indexed"] = _fetch_pages_indexed(host)
    return data


def _build_backlinks_map(brands):
    """Return {competitor_id_or_None: backlink_dict} fetched concurrently.
    Falls back to empty dict for any brand that fails — those cells render N/A.
    """
    result = {}
    if not brands:
        return result
    with ThreadPoolExecutor(max_workers=min(8, len(brands))) as pool:
        futures = {pool.submit(_fetch_brand_backlinks, b): b for b in brands}
        for fut, brand in futures.items():
            try:
                result[brand["competitor_id"]] = fut.result(timeout=60) or _BACKLINK_EMPTY.copy()
            except Exception as exc:
                logger.warning("Backlink fetch failed for %s: %s", brand.get("name"), exc)
                result[brand["competitor_id"]] = _BACKLINK_EMPTY.copy()
    return result


def _cell_value(num):
    """None → "N/A", otherwise integer (so Excel renders a number, not a string)."""
    if num is None:
        return "N/A"
    try:
        return int(num)
    except (TypeError, ValueError):
        return "N/A"


def _write_header_label(ws, cell_ref, value, *, bold=True, fill=None):
    cell = ws[cell_ref]
    cell.value = value
    if bold:
        cell.font = Font(bold=True)
    if fill:
        cell.fill = PatternFill("solid", fgColor=fill)
    cell.alignment = Alignment(vertical="center", wrap_text=True)


def _build_workbook(domain, brands, platforms, mention_matrix, brand_totals,
                    brand_visibility, your_llm_citations, backlinks_map=None,
                    period_label=None):
    backlinks_map = backlinks_map or {}
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

    # ---------- Period header (Q1a) ----------
    # Tiny meta row above the data so users know the time-range semantics
    # (Mentions are period-summed, Visibility is snapshot-of-latest).
    if period_label:
        cell = ws.cell(row=1, column=2, value=period_label)
        cell.font = Font(italic=True, color="555555")
        cell.alignment = Alignment(vertical="center")
        # Merge across C + the brand columns for visibility.
        last_col = 3 + max(len(brands), 1)
        ws.merge_cells(start_row=1, start_column=2, end_row=1, end_column=last_col)
        ws.row_dimensions[1].height = 20

    # ---------- Block 1 ----------
    _write_header_label(ws, "B2", "Pillars", fill=BLOCK_FILL)
    _write_header_label(ws, "C2", "URL", fill=BLOCK_FILL)

    _write_header_label(ws, "C3", "Defination", fill=HEADER_FILL)
    for i, b in enumerate(brands):
        _write_header_label(ws, ws.cell(row=3, column=4 + i).coordinate, b["name"],
                            fill=HEADER_FILL)

    # Row 4: AI Visibility Score (shifted down by 1 to make room for the
    # period-info header on row 1).
    ws["B4"] = "AI Visibility Score"
    ws["B4"].font = Font(bold=True)
    ws["C4"] = VISIBILITY_DEFINITION
    ws["C4"].alignment = Alignment(wrap_text=True, vertical="center")
    for i, b in enumerate(brands):
        score = brand_visibility.get(b["competitor_id"], 0.0)
        ws.cell(row=4, column=4 + i, value=f"{int(round(score))}/100")

    # Rows 5..N: per-LLM mentions
    row = 5
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

    # Rows for Referring Domains / Total Backlinks / Pages Indexed in SERP.
    # Values are populated per-brand from the backlinks provider (DataForSEO/Moz)
    # and Scrapingdog's site: query. Unconfigured providers leave the cell as N/A.
    block1_metric_keys = (
        ("Number of Referring Domains", "referring_domains"),
        ("Number of Total Backlinks", "total_backlinks"),
        ("Pages Indexed in SERP", "pages_indexed"),
    )
    for label, key in block1_metric_keys:
        ws.cell(row=row, column=2, value=label).font = Font(bold=True)
        for i, b in enumerate(brands):
            payload = backlinks_map.get(b["competitor_id"]) or {}
            ws.cell(row=row, column=4 + i, value=_cell_value(payload.get(key)))
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

    # ---------- Block 3: Backlink Portfolio ----------
    row += 1
    _write_header_label(ws, ws.cell(row=row, column=3).coordinate,
                        "Backlink Portfolio", fill=BLOCK_FILL)
    for i, b in enumerate(brands):
        _write_header_label(ws, ws.cell(row=row, column=4 + i).coordinate,
                            b["name"], fill=BLOCK_FILL)
    row += 1
    # (label, lookup-key) — sub-rows pull CAT A/B/C from the same backlinks payload.
    portfolio_rows = (
        ("Referring Domains", "referring_domains"),
        ("CAT A", "cat_a_domains"),
        ("CAT B", "cat_b_domains"),
        ("CAT C", "cat_c_domains"),
        ("Number of Total Backlinks", "total_backlinks"),
        ("CAT A", "cat_a_backlinks"),
        ("CAT B", "cat_b_backlinks"),
        ("CAT C", "cat_c_backlinks"),
    )
    for label, key in portfolio_rows:
        ws.cell(row=row, column=3, value=label)
        for i, b in enumerate(brands):
            payload = backlinks_map.get(b["competitor_id"]) or {}
            ws.cell(row=row, column=4 + i, value=_cell_value(payload.get(key)))
        row += 1

    return wb


# ---------------------------------------------------------------------------
# Insight sheets (tabs 1-9)
#
# The original workbook was a single competitor-comparison grid, so an export
# carried almost nothing about the domain's OWN performance — the thing the
# Insights page spends most of its area showing. These sheets add it.
#
# Their figures come from dashboard_summary's own response rather than from
# re-derived queries. A report that disagrees with the page it was exported
# from is worse than no report, and the trend/visibility logic in particular
# (period vs running totals, window sizing, brand matching) is too easy to
# reimplement subtly differently.
# ---------------------------------------------------------------------------

_TABLE_HEADER_FILL = "E8E8FF"


def _write_table(ws, headers, rows, widths=None, note=None):
    """Write a simple header + rows table, starting at A1 (or A2 with a note)."""
    top = 1
    if note:
        cell = ws.cell(row=1, column=1, value=note)
        cell.font = Font(italic=True, color="555555")
        ws.row_dimensions[1].height = 18
        top = 3

    for i, header in enumerate(headers, start=1):
        cell = ws.cell(row=top, column=i, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor=_TABLE_HEADER_FILL)
        cell.alignment = Alignment(vertical="center")

    for r, row in enumerate(rows, start=top + 1):
        for c, value in enumerate(row, start=1):
            ws.cell(row=r, column=c, value=value)

    for i, width in enumerate(widths or [], start=1):
        ws.column_dimensions[ws.cell(row=top, column=i).column_letter].width = width

    ws.freeze_panes = ws.cell(row=top + 1, column=1)


def _pct(value):
    return None if value is None else round(float(value), 2)


def _cited_page_rows(domain_id, start_date, end_date, platform_filter, domain_host):
    """Every page on the domain that AI cited, with how often and by whom.

    live_domain_window_metrics computes this set to size the Cited Pages metric
    and then throws the URLs away, keeping only len(). The report is the one
    place the actual pages are worth naming, so the walk is repeated here with
    the identical host-matching rule.
    """
    if not domain_host:
        return []

    start_dt, end_dt = _dashboard_datetime_window(start_date, end_date)
    qs = PromptAnalytics.objects.annotate(
        _window_dt=Coalesce('tracked_at', 'created_at'),
    ).filter(
        prompt__group__domain_id=domain_id,
        track_status='COMP',
        _window_dt__gte=start_dt,
        _window_dt__lte=end_dt,
    )
    if platform_filter:
        qs = qs.filter(platform=platform_filter)

    pages = {}
    for platform, clist in qs.values_list('platform', 'citation_list'):
        if not isinstance(clist, list):
            continue
        for entry in clist:
            url = _citation_entry_url(entry)
            if not url:
                continue
            host = _url_host(url)
            if not host:
                continue
            if host == domain_host or host.endswith('.' + domain_host):
                page = pages.setdefault(
                    _canonical_page(url), {'count': 0, 'platforms': set()}
                )
                page['count'] += 1
                page['platforms'].add(platform)

    return [
        [url, data['count'], ", ".join(sorted(data['platforms']))]
        for url, data in sorted(
            pages.items(), key=lambda kv: kv[1]['count'], reverse=True
        )
    ]


# Written once here rather than left to the reader. Nearly every metric on this
# page has a near-namesake that counts something else — "Your Citations" against
# "Sources Cited" being the pair that caused the most confusion — and a
# spreadsheet travels further from its context than the page does.
_DEFINITIONS = [
    ["Mentions", "Times AI answers named your brand, summed over the window."],
    ["Your Citations", "Times AI answers linked to a page on YOUR domain. "
                       "Counts each link, so one page cited twice counts twice."],
    ["Sources Cited", "Every URL cited in the answers, yours and everyone "
                      "else's. The denominator of Citation Share, not a figure "
                      "about your brand."],
    ["Cited Pages", "Distinct pages on your domain that were cited. The same "
                    "links as Your Citations, counted once per page."],
    ["Citation Share", "Your Citations divided by Sources Cited, as a percent. "
                       "How much of what AI cites is you."],
    ["Visibility Score", "0-100 score over every answer in the window, pooled. "
                         "Not the average of the per-period points."],
    ["Avg Position", "Average rank of your brand where it appears. Lower is "
                     "better."],
    ["Share of Voice", "Your share of mentions across you plus your TRACKED "
                       "competitors. Moves when the competitor list is edited. "
                       "Read from the latest available day, not the window."],
    ["AI Sessions", "Google Analytics sessions that arrived from an AI "
                    "platform, from the nightly sync."],
    ["Periods", "Trend rows close a period, not a day. Period length follows "
                "the engine's run cadence, so rows are not evenly spaced."],
]


def _add_insight_sheets(wb, request, domain, start_date, end_date, platform_filter):
    """Append tabs 1-9 to the workbook, sourced from dashboard_summary."""
    # Re-entering the view guarantees the report and the page agree. It is a
    # plain authenticated GET against the same params, so the only cost is
    # repeating its queries.
    summary = dashboard_summary(request._request)
    if summary.status_code != 200:
        logger.warning(
            "dashboard_export: summary returned %s for domain %s; "
            "insight sheets skipped",
            summary.status_code, domain.id,
        )
        return
    data = summary.data or {}
    metrics = data.get("metrics") or {}
    window_note = (
        f"{_domain_display_name(domain)} · "
        f"{start_date.isoformat()} → {end_date.isoformat()}"
        + (f" · {platform_filter}" if platform_filter else " · all platforms")
    )

    # ---- 1. Summary ----
    def _delta(key):
        value = metrics.get(key)
        return "N/A" if value is None else value

    _write_table(
        wb.create_sheet("Summary"),
        ["Metric", "Value", "Change vs previous period"],
        [
            ["Total Prompts", metrics.get("total_prompts"), ""],
            ["Mentions", metrics.get("total_mentions"), _delta("mentions_change")],
            ["Your Citations", metrics.get("total_brand_citations"),
             _delta("brand_citations_change")],
            ["Cited Pages", metrics.get("total_cited_pages"),
             _delta("cited_pages_change")],
            ["Citation Share (%)", _pct(metrics.get("citation_share")),
             _delta("citation_share_change")],
            ["Sources Cited (all URLs)", metrics.get("total_citations"),
             _delta("citations_change")],
            ["Visibility Score", metrics.get("visibility_score"),
             _delta("visibility_change")],
            ["Avg Position", metrics.get("avg_position"), _delta("position_change")],
            ["Active Alerts", metrics.get("active_alerts"), ""],
        ],
        widths=[30, 18, 28],
        note=window_note,
    )

    # ---- 2. Trend ----
    trends = data.get("trends") or []
    trend_note = (
        "Per-period activity."
        if data.get("trends_are_period")
        else "RUNNING TOTALS as at each date, not activity within the period — "
             "the engine has not yet written per-period counts for this domain."
    )
    _write_table(
        wb.create_sheet("Trend"),
        ["Period start", "Period end", "Label", "Mentions", "Citations",
         "Cited Pages", "Visibility Score"],
        [
            [t.get("period_start_iso"), t.get("date_iso"), t.get("date"),
             t.get("mentions"), t.get("citations"), t.get("cited_pages"),
             t.get("visibility")]
            for t in trends
        ],
        widths=[14, 14, 12, 12, 12, 13, 16],
        note=f"{window_note} · {trend_note}",
    )

    # ---- 3. By Platform ----
    platform_rows = data.get("platforms") or []
    total_mentions = sum((p.get("mention_count") or 0) for p in platform_rows)
    _write_table(
        wb.create_sheet("By Platform"),
        ["Platform", "Mentions", "Share of mentions (%)", "Avg Position",
         "Your Citations", "Cited Pages"],
        [
            [
                p.get("platform"),
                p.get("mention_count"),
                _pct((p.get("mention_count") or 0) / total_mentions * 100)
                if total_mentions else 0.0,
                p.get("avg_position"),
                p.get("citations"),
                p.get("cited_pages"),
            ]
            for p in platform_rows
        ],
        widths=[18, 12, 22, 14, 16, 13],
        note=window_note + " · A platform with 0 mentions still ran; it simply "
                           "did not name the brand.",
    )

    # ---- 4. Cited Pages ----
    domain_host = _url_host(domain.url) if domain.url else None
    page_rows = _cited_page_rows(
        domain.id, start_date, end_date, platform_filter, domain_host
    )
    _write_table(
        wb.create_sheet("Cited Pages"),
        ["Page URL", "Times cited", "Cited by"],
        page_rows,
        widths=[80, 14, 32],
        note=window_note + " · Distinct pages on your own domain. Times cited "
                           "sums to Your Citations; the row count is Cited Pages.",
    )

    # ---- 5. Mentions ----
    mentions = data.get("recent_mentions") or []
    _write_table(
        wb.create_sheet("Mentions"),
        ["Date", "Platform", "Prompt", "Position", "Sentiment",
         "Sentiment score", "Citations"],
        [
            [
                m.get("created_at"),
                m.get("platform"),
                m.get("prompt"),
                m.get("position"),
                m.get("sentiment"),
                m.get("sentiment_score"),
                m.get("citations"),
            ]
            for m in mentions
        ],
        widths=[28, 16, 60, 10, 12, 16, 12],
        # Said plainly rather than left to be discovered: the page shows a
        # "Recent Mentions" list capped at 10 and the export carries the same
        # list, so this sheet is a sample. A reader who assumes it is every
        # mention in the window would badly undercount — Mentions on the
        # Summary sheet is the real total.
        note=window_note + " · MOST RECENT 10 ONLY — this is the page's Recent "
                           "Mentions list, not every mention in the window. "
                           "See Summary for the full count.",
    )

    # ---- 7. By Country ----
    _write_table(
        wb.create_sheet("By Country"),
        ["Country", "Code", "Mentions", "Share (%)"],
        [
            [c.get("name"), c.get("code"), c.get("count"), _pct(c.get("percentage"))]
            for c in (data.get("countries") or [])
        ],
        widths=[24, 10, 12, 12],
        note=window_note + " · Reflects where each prompt was asked from, not "
                           "where the reader is.",
    )

    # ---- 8. AI Traffic ----
    # Read straight from the nightly GA sync rather than GA4: the same table the
    # page reads, so an export never burns the property's report quota.
    traffic = (
        GAAITrafficDaily.objects
        .filter(domain_id=domain.id, date__gte=start_date, date__lte=end_date)
        .exclude(platform=GAAITrafficDaily.ALL_PLATFORMS)
        .order_by("date", "platform")
    )
    _write_table(
        wb.create_sheet("AI Traffic"),
        ["Date", "Platform", "Sessions", "Users", "Page Views", "Conversions",
         "Avg Duration (s)"],
        [
            [r.date, r.platform, r.sessions, r.users, r.page_views,
             r.conversions, float(r.avg_duration or 0)]
            for r in traffic
        ],
        widths=[14, 20, 12, 12, 14, 14, 18],
        note=window_note + " · From the nightly Google Analytics sync. Empty "
                           "when GA is not connected.",
    )

    # ---- 9. Definitions ----
    _write_table(
        wb.create_sheet("Definitions"),
        ["Term", "What it counts"],
        _DEFINITIONS,
        widths=[24, 110],
    )


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

    # Tenant isolation — same rule as dashboard_summary. This endpoint takes the
    # same parameters and had the same hole: any authenticated user could export
    # another organisation's report by changing domain_id. 404, not 403, so the
    # response never confirms that someone else's domain exists.
    if not user_can_access_domain(request.user, domain_id, request):
        return Response({"error": "Domain not found or not in your organization"},
                        status=status.HTTP_404_NOT_FOUND)

    try:
        days = int(request.query_params.get("days", 30))
    except (TypeError, ValueError):
        days = 30

    platform_filter = _normalize_platform_filter(request.query_params.get("llm_model"))
    domain = get_object_or_404(Domain, id=domain_id)

    # Optional explicit date range overrides `days`. Accepts ISO YYYY-MM-DD.
    start_param = request.query_params.get("start_date")
    end_param = request.query_params.get("end_date")
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days - 1)
    if start_param or end_param:
        try:
            if end_param:
                end_date = datetime.strptime(end_param, "%Y-%m-%d").date()
            if start_param:
                start_date = datetime.strptime(start_param, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "start_date and end_date must be YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if start_date > end_date:
            return Response(
                {"error": "start_date cannot be after end_date"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
        latest_day = None
        latest_rows = sov_qs.none()

    # Q1b: mentions are now summed across the period (every snapshot day in
    # the date range) so a competitor with mentions earlier in the window
    # doesn't show as 0 just because the latest day was quiet.
    period_rows = sov_qs

    brands = _build_brand_columns(domain, latest_rows)
    platforms = _platforms_for_report(period_rows)
    if platform_filter:
        # Honor the LLM dropdown: only include the selected platform's row.
        platforms = [platform_filter]

    matrix = _mention_matrix(period_rows, brands, platforms)
    totals = _brand_totals(period_rows, brands)
    # Visibility remains a current-state percentage from the latest day.
    visibility = _brand_visibility(latest_rows, brands)
    your_citations = _your_brand_llm_citations(domain_id, start_date, end_date)
    # Per-brand backlink metrics (referring domains, total backlinks, CAT A/B/C,
    # pages indexed in SERP). Runs in parallel; if no provider is configured each
    # brand returns an empty payload and the cells render N/A — same as before.
    #
    # OPT-IN, because this is the entire cost of an export. Measured on Appkodes
    # (6 brands): the whole export took 40.6s, of which backlinks and
    # pages-indexed were 45.7s of wall-clock across the pool — one brand hit the
    # 30s read timeout on its own — while every other sheet together took 1.8s.
    # The frontend buffers the response into a blob before saving, so nothing
    # reaches disk until the last byte and navigating away discards the lot;
    # a 40s default made that easy to trigger. Skipped unless asked for, which
    # puts a normal export at ~2s.
    include_backlinks = str(
        request.query_params.get("include_backlinks", "")
    ).lower() in ("1", "true", "yes")
    backlinks_map = _build_backlinks_map(brands) if include_backlinks else {}

    period_label = (
        f"Mentions summed: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}"
        f" · Visibility snapshot: {latest_day.strftime('%Y-%m-%d') if latest_day else 'n/a'}"
    )
    if not include_backlinks:
        # Without this the empty backlink cells read as "this brand has no
        # backlinks" rather than "we did not go and look".
        period_label += (
            " · Backlinks & pages-indexed NOT FETCHED — re-export with"
            " 'Include backlinks' to populate them"
        )

    wb = _build_workbook(domain, brands, platforms, matrix, totals, visibility,
                         your_citations, backlinks_map=backlinks_map,
                         period_label=period_label)

    # The competitor grid is worth keeping but is not the report on its own, so
    # the domain's own numbers follow it. Failing to build them must not cost
    # the user the sheet that already worked.
    try:
        _add_insight_sheets(wb, request, domain, start_date, end_date,
                            platform_filter)
    except Exception:
        logger.exception(
            "dashboard_export: insight sheets failed for domain %s; "
            "returning the AI Visibility sheet alone", domain_id,
        )

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
