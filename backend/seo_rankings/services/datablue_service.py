"""
DataBlue SERP service — backend side.

Replaces ScrapingDog for SEO keyword ranking. Sync-only: backend call sites
(per-keyword from views.py and scraping_service.py) make individual calls,
batch parallelism lives in the engine.
"""
import logging
import urllib.parse
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# DataBlue SERP endpoint (/v1/data/google/serp — GET + query params). Read via
# _cfg at call time so the URL can be overridden in settings/.env without a code
# change. Supports the country / mobile / language / domain / location / uule /
# pages / advanced params that _build_params forwards below.
DEFAULT_DATABLUE_API_URL = "https://api.datablue.dev/v1/data/google/serp"

# A Google results page holds ~10 organic results. Used to convert the
# configured page count into the deepest rank a scrape can observe.
RESULTS_PER_PAGE = 10


def _cfg(name: str, default):
    return getattr(settings, name, default)


def _api_url():
    return _cfg("DATABLUE_API_URL", DEFAULT_DATABLUE_API_URL)


def _is_usable(raw) -> bool:
    """True only if DataBlue returned a real SERP we can rank against.

    DataBlue can intermittently return success=true with an EMPTY
    organic_results list (the scrape produced nothing). A genuine Google query
    always returns a full SERP, so an empty list means a failed scrape — NOT
    "not ranked in top N" (that case still returns ~10 results, just without the
    target domain). Treating empty as a failure makes the caller retry next
    cycle instead of overwriting a good rank with 0.
    """
    if not isinstance(raw, dict):
        return False
    if not raw.get("success", True):
        return False
    return bool(raw.get("organic_results"))


def _normalize_organic(organic):
    """Map DataBlue field names to the shape parser_service expects.

    DataBlue returns:  position, url, title, snippet
    Parsers expect:    rank,     link, title, snippet, displayed_link
    """
    for item in organic:
        if not isinstance(item, dict):
            continue

        if "rank" not in item and "position" in item:
            try:
                item["rank"] = int(item.get("position") or 0)
            except (TypeError, ValueError):
                item["rank"] = 0

        if "link" not in item and "url" in item:
            item["link"] = item.get("url", "")

        if "displayed_link" not in item:
            # DataBlue returns "displayed_url" directly; prefer it, else derive from link.
            if item.get("displayed_url"):
                item["displayed_link"] = item.get("displayed_url", "")
            else:
                try:
                    p = urllib.parse.urlparse(item.get("link", ""))
                    item["displayed_link"] = (p.netloc + p.path).rstrip("/")
                except Exception:
                    item["displayed_link"] = item.get("link", "")

        if "snippet" not in item:
            item["snippet"] = ""
        if "title" not in item:
            item["title"] = ""

    return organic


def serp_pages() -> int:
    """How many Google result pages each keyword scrape requests (1-5).

    Derived from DATABLUE_NUM_RESULTS (~10 results/page) so the existing
    depth/cost config keeps working, with DATABLUE_PAGES as an explicit
    override. Read at call time so an .env change takes effect on restart
    without a code deploy.
    """
    try:
        cfg_pages = int(_cfg("DATABLUE_PAGES", 0) or 0)
    except (TypeError, ValueError):
        cfg_pages = 0
    if cfg_pages > 0:
        return max(1, min(5, cfg_pages))

    try:
        num = int(_cfg("DATABLUE_NUM_RESULTS", 10) or 10)
    except (TypeError, ValueError):
        num = 10
    return max(1, min(5, (num + 9) // 10))


def max_tracked_rank() -> int:
    """The deepest rank a scrape can possibly see, ~10 results per page.

    Anything below this is indistinguishable from "not ranking at all", so the
    UI labels unranked keywords ">{max_tracked_rank}". Hardcoding that label is
    how it came to read ">100" while only the first 10 results were ever
    fetched.
    """
    return serp_pages() * RESULTS_PER_PAGE


def _build_params(
    keyword_text: str,
    isocode: str,
    language_code: str,
    platform: str = "",
    region: str = "",
    location: str = "",
    uule: str = "",
) -> dict:
    """Build the DataBlue /v1/data/google/serp request query params (GET).

    The endpoint is page-based: ``pages`` (1-5, ~10 results each). We derive
    ``pages`` from DATABLUE_NUM_RESULTS so the existing depth/cost config keeps
    working (10 -> 1 page), with DATABLUE_PAGES as an explicit override. country /
    mobile (desktop|mobile) / language / domain / location / uule are each
    forwarded only when set, so every keyword is scraped exactly as configured on
    its SeoKeywordRank without changing defaults. ``advanced`` (DATABLUE_ADVANCED,
    default false) selects the cheaper organic-focused SERP mode.
    """
    params = {"query": (keyword_text or "")[:2048]}

    params["pages"] = serp_pages()

    # advanced=false → cheaper organic-focused SERP (1 credit/page vs 2).
    params["advanced"] = "true" if _cfg("DATABLUE_ADVANCED", False) else "false"

    if language_code:
        params["language"] = language_code
    if isocode:
        params["country"] = str(isocode).lower()

    # Device. Defaults to DATABLUE_PLATFORM (desktop) when the caller omits it.
    # The serp endpoint takes a ``mobile`` boolean instead of v2's platform string.
    plat = (platform or _cfg("DATABLUE_PLATFORM", "desktop") or "").strip().lower()
    if plat == "mobile":
        params["mobile"] = "true"
    elif plat == "desktop":
        params["mobile"] = "false"

    # region holds the Google domain configured per keyword in the DB (model
    # default "google.com", e.g. "google.co.in"). Forward it for EVERY keyword
    # exactly as stored — no www. prefixing — so the SERP is scraped on the exact
    # domain configured. Falls back to DATABLUE_GOOGLE_DOMAIN when no region.
    dom = (region or _cfg("DATABLUE_GOOGLE_DOMAIN", "") or "").strip()
    if dom:
        params["domain"] = dom

    if location:
        params["location"] = location
    if uule:
        params["uule"] = uule
    return params


def fetch_one(
    keyword_text: str,
    isocode: str = "",
    language_code: str = "",
    platform: str = "",
    region: str = "",
    location: str = "",
    uule: str = "",
) -> Optional[dict]:
    """Sync single-keyword DataBlue call.

    ``platform`` (desktop|mobile), ``region`` (Google domain), ``location`` and
    ``uule`` are optional params; omitting them preserves the prior behavior.

    Returns the parsed JSON response (with normalized organic_results) or None
    on any failure (no key, non-200, timeout, JSON parse error, empty results).
    """
    api_key = _cfg("DATABLUE_API_KEY", "")
    if not api_key:
        logger.error("[DataBlue] DATABLUE_API_KEY not configured")
        return None

    params = _build_params(keyword_text, isocode, language_code, platform, region, location, uule)
    timeout = _cfg("DATABLUE_TIMEOUT", 60)

    try:
        resp = requests.get(
            _api_url(),
            headers={"Authorization": f"Bearer {api_key}"},
            params=params,
            timeout=timeout,
        )
    except requests.Timeout:
        logger.warning(f"[DataBlue] Timeout for '{keyword_text}'")
        return None
    except requests.RequestException as e:
        logger.warning(f"[DataBlue] Request failed for '{keyword_text}': {e}")
        return None

    if resp.status_code != 200:
        logger.warning(f"[DataBlue] Non-200 ({resp.status_code}) for '{keyword_text}'")
        return None

    try:
        raw = resp.json()
    except ValueError as je:
        logger.warning(f"[DataBlue] JSON parse failed for '{keyword_text}': {je}")
        return None

    if not isinstance(raw, dict):
        return None

    organic = raw.get("organic_results", []) or []
    raw["organic_results"] = _normalize_organic(organic)
    # Usable only when success=true AND organic is non-empty. success=false or an
    # empty SERP (a failed v2 scrape) → return None so the caller retries instead
    # of recording a spurious rank 0. See _is_usable.
    if not _is_usable(raw):
        logger.warning(
            f"[DataBlue] Empty/failed SERP for '{keyword_text}' "
            f"(success={raw.get('success')}, organic={len(organic)}) — returning None"
        )
        return None
    return raw
