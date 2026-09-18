"""Google rankings for an audit, from DataForSEO.

Why this exists: seo_ranking_processor.fetch_serp_data() asks DataBlue, and
DATABLUE_API_KEY is not set on every deployment. DataForSEO is already wired in
for search volume (dataforseo_volume) and backlinks (backlinks_processor) with
the same credentials, and its SERP endpoint is on the same account — so an
audit can rank keywords without a second vendor.

The response is normalised into the ScrapingDog-ish shape that
seo_ranking_processor.parse_json_serp_response() already reads, so the parser,
the scoring and the report stay exactly as they are. This module only speaks
HTTP and reshapes.

Endpoint: POST /v3/serp/google/organic/live/advanced — one keyword per request,
billed per request. Measured 2026-09-16 on the live account: $0.0035 at
depth=20 (the published rate is $0.002 for a shallower depth). The async
task_post flow is cheaper at $0.0006 but needs a post-then-poll round trip,
which is the wrong trade inside a pipeline the user is watching run.

A failed lookup raises. That is deliberate: the caller must be able to tell
"this brand does not rank" from "we never got an answer", because writing the
second down as the first produces a report that tells a prospect they rank for
nothing on Google when in truth nobody asked.
"""
import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings

from core.dataforseo_volume import ISO_TO_LOCATION_CODE, LOCATION_FALLBACK

logger = logging.getLogger(__name__)

LIVE_URL = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"
SANDBOX_URL = "https://sandbox.dataforseo.com/v3/serp/google/organic/live/advanced"

# How deep to read the result page. 20 covers "top 10" plus the striking-distance
# band (11-20) that audit_scoring reports on; asking for more costs the same per
# request but returns payload nobody reads.
DEFAULT_DEPTH = 20

REQUEST_TIMEOUT = 60

# Cost per request, for reporting only — the API bills what it bills.
COST_PER_KEYWORD = 0.0035


def _credentials():
    login = (getattr(settings, "DATAFORSEO_LOGIN", "") or "").strip().strip("'\"")
    password = (getattr(settings, "DATAFORSEO_PASSWORD", "") or "").strip().strip("'\"")
    if not login or not password:
        raise RuntimeError("DataForSEO credentials are not configured")
    return login, password


def _url() -> str:
    if getattr(settings, "DATAFORSEO_USE_SANDBOX", False):
        return SANDBOX_URL
    return LIVE_URL


def location_code_for(isocode: str) -> int:
    return ISO_TO_LOCATION_CODE.get((isocode or "").strip().lower(), LOCATION_FALLBACK)


def _normalise(result: Dict[str, Any]) -> Dict[str, Any]:
    """DataForSEO items[] -> the shape parse_json_serp_response() expects.

    DataForSEO returns one flat `items` list where every SERP element carries a
    `type`; the parser wants organic results in their own list and the special
    blocks under their own keys.
    """
    organic = []
    out: Dict[str, Any] = {
        "search_information": {"total_results": result.get("se_results_count")},
        "organic_results": organic,
    }

    for item in result.get("items") or []:
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        if kind == "organic":
            organic.append({
                "link": item.get("url") or "",
                "rank": item.get("rank_group") or item.get("rank_absolute") or 0,
                "title": item.get("title") or "",
                "snippet": item.get("description") or "",
            })
        elif kind == "featured_snippet" and "answer_box" not in out:
            out["answer_box"] = {
                "title": item.get("title") or "",
                "snippet": item.get("description") or item.get("featured_title") or "",
                "link": item.get("url") or "",
            }
        elif kind == "knowledge_graph" and "knowledge_graph" not in out:
            out["knowledge_graph"] = {
                "title": item.get("title") or "",
                "description": item.get("description") or "",
            }
        elif kind in ("paid", "ads") :
            out.setdefault("ads", []).append({
                "title": item.get("title") or "",
                "link": item.get("url") or "",
            })

    return out


def fetch_serp(
    keyword: str,
    isocode: str,
    language_code: str = "en",
    device: str = "desktop",
    depth: int = DEFAULT_DEPTH,
    timeout: int = REQUEST_TIMEOUT,
) -> Optional[Dict[str, Any]]:
    """One keyword's Google results, normalised. Raises on any failure.

    Returns None only when DataForSEO answered successfully but had no result
    for the keyword — a real "nothing found", as distinct from an error.
    """
    payload = [{
        "keyword": keyword,
        "location_code": location_code_for(isocode),
        "language_code": language_code or "en",
        "device": device,
        "depth": depth,
    }]

    response = requests.post(_url(), auth=_credentials(), json=payload, timeout=timeout)
    response.raise_for_status()
    body = response.json()

    if body.get("status_code") != 20000:
        raise RuntimeError(f"DataForSEO error {body.get('status_code')}: {body.get('status_message')}")

    tasks = body.get("tasks") or []
    if not tasks:
        raise RuntimeError("DataForSEO returned no task")
    task = tasks[0]
    if task.get("status_code") != 20000:
        raise RuntimeError(f"DataForSEO task error {task.get('status_code')}: {task.get('status_message')}")

    results = task.get("result") or []
    if not results:
        return None
    return _normalise(results[0])
