"""
DataBlue SERP service — engine side.

Replaces ScrapingDog for SEO keyword ranking. Two entry points:

    fetch_one(keyword, isocode, language) -> dict | None
        Single sync call. Used by per-keyword paths (Celery process_seo_keyword_task,
        competitor analysis fallback).

    fetch_many(items, on_result=None) -> list[dict]
        Async batch. All keywords dispatched concurrently via httpx.AsyncClient +
        asyncio.Semaphore. If on_result(...) is supplied, it runs in a thread pool
        AS each SERP response lands — DB writes pipeline with in-flight HTTP calls.
        Sync entry point: callers (Django/Celery) don't see asyncio.

Direct port of rankmax/engine_dev_env/project/machine/automation_proxy.py.
"""
import asyncio
import concurrent.futures as _cf
import logging
import urllib.parse
from typing import Callable, Optional

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

# DataBlue SERP endpoint (/v1/data/google/serp — GET + query params). Read via
# _cfg at call time so the URL can be overridden in settings/.env without a code
# change. Supports the country / mobile / language / domain / location / uule /
# pages / advanced params that _build_params forwards below.
DEFAULT_DATABLUE_API_URL = "https://api.datablue.dev/v1/data/google/serp"


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

    # num_results (~10/page) -> pages, capped to 1-5; DATABLUE_PAGES overrides.
    try:
        num = int(_cfg("DATABLUE_NUM_RESULTS", 10) or 10)
    except (TypeError, ValueError):
        num = 10
    derived_pages = max(1, min(5, (num + 9) // 10))
    try:
        cfg_pages = int(_cfg("DATABLUE_PAGES", 0) or 0)
    except (TypeError, ValueError):
        cfg_pages = 0
    # DATABLUE_PAGES <= 0 means "derive from num_results"; otherwise cap to 1-5.
    params["pages"] = max(1, min(5, cfg_pages)) if cfg_pages > 0 else derived_pages

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

    # region holds a Google domain (model default "google.com"). Only forward an
    # explicit non-default domain — otherwise let DataBlue auto-pick the
    # country-correct domain (e.g. www.google.co.in for country=in).
    dom = (region or _cfg("DATABLUE_GOOGLE_DOMAIN", "") or "").strip()
    if dom and dom not in ("google.com", "www.google.com"):
        params["domain"] = dom if dom.startswith("www.") else f"www.{dom}"

    if location:
        params["location"] = location
    if uule:
        params["uule"] = uule
    return params


# ---------------------------------------------------------------------------
# ASYNC LAYER — used by fetch_many
# ---------------------------------------------------------------------------
async def _fetch_one_async(client, sem, item_id, item_data, api_key, timeout):
    """Single DataBlue request, concurrency-limited by semaphore."""
    params = _build_params(
        item_data.get("keyword", ""),
        item_data.get("isocode", ""),
        item_data.get("language_code") or item_data.get("language", ""),
        platform=item_data.get("platform", ""),
        region=item_data.get("region", ""),
        location=item_data.get("location", ""),
        uule=item_data.get("uule", ""),
    )

    async with sem:
        try:
            resp = await client.get(
                _api_url(),
                headers={"Authorization": f"Bearer {api_key}"},
                params=params,
                timeout=timeout,
            )
            if resp.status_code == 200:
                try:
                    raw = resp.json()
                    organic = raw.get("organic_results", []) or []
                    raw["organic_results"] = _normalize_organic(organic)
                    # Usable only when success=true AND organic is non-empty.
                    # An empty list (even with success=true) is a failed v2
                    # scrape, so flag the item failed → it retries next cycle
                    # rather than recording a spurious rank 0. See _is_usable.
                    usable = _is_usable(raw)
                    if not usable:
                        logger.warning(
                            f"[DataBlue] Empty/failed SERP for item {item_id} "
                            f"(success={raw.get('success')}, organic={len(organic)}) — will retry"
                        )
                    return {
                        "item_id": item_id,
                        "status": resp.status_code,
                        "data": raw,
                        "success": usable,
                    }
                except Exception as je:
                    logger.warning(f"[DataBlue] JSON parse failed for item {item_id}: {je}")
                    return {"item_id": item_id, "status": resp.status_code, "data": None, "success": False}

            # Include response body so auth/billing failures (401, 402, 403)
            # are visible in the worker log instead of looking like a generic
            # scraping error.
            body_snippet = (resp.text or '')[:300].replace('\n', ' ')
            logger.warning(
                f"[DataBlue] Non-200 for item {item_id}: status={resp.status_code} "
                f"kw={params.get('query', '')[:60]} body={body_snippet}"
            )
            return {"item_id": item_id, "status": resp.status_code, "data": None, "success": False}

        except httpx.TimeoutException:
            logger.warning(f"[DataBlue] Timeout after {timeout}s for item {item_id}")
            return {"item_id": item_id, "status": "timeout", "data": None, "success": False}
        except Exception as e:
            logger.warning(f"[DataBlue] Exception for item {item_id}: {e}")
            return {"item_id": item_id, "status": "error", "data": None, "success": False}


async def _pipeline_async(items_dict, concurrency, api_key, timeout, on_result):
    """Dispatches fetches concurrently. If on_result is given, runs it in a
    thread pool as each fetch result lands — so DB writes start while later
    fetches are still in flight (rankmax pattern).
    """
    sem = asyncio.Semaphore(concurrency)
    results = []

    limits = httpx.Limits(
        max_connections=concurrency + 5,
        max_keepalive_connections=concurrency,
    )
    loop = asyncio.get_event_loop()

    async def _fetch_then_dispatch(item_id, item_data, db_pool, client):
        fetch_result = await _fetch_one_async(client, sem, item_id, item_data, api_key, timeout)
        if on_result is None:
            return {"fetch": fetch_result, "cb": None}
        try:
            cb_result = await loop.run_in_executor(db_pool, on_result, fetch_result)
        except Exception as cbe:
            logger.error(f"[DataBlue] on_result callback error for item {item_id}: {cbe}", exc_info=True)
            cb_result = None
        return {"fetch": fetch_result, "cb": cb_result}

    db_pool_size = max(1, concurrency) if on_result is not None else 1
    with _cf.ThreadPoolExecutor(max_workers=db_pool_size) as db_pool:
        async with httpx.AsyncClient(limits=limits) as client:
            tasks = [
                asyncio.create_task(_fetch_then_dispatch(item_id, item_data, db_pool, client))
                for item_id, item_data in items_dict.items()
            ]
            for coro in asyncio.as_completed(tasks):
                results.append(await coro)

    return results


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------
def fetch_many(
    items: dict,
    on_result: Optional[Callable[[dict], object]] = None,
    concurrency: Optional[int] = None,
) -> list:
    """Sync entry point for batch fetch.

    Args:
        items: dict mapping item_id -> {"keyword": str, "isocode": str, "language_code": str}
        on_result: optional callable(fetch_result_dict) executed in a thread as
            each fetch lands. Use this to start DB writes while later fetches
            are still in flight (pipelined fetch + process).
        concurrency: max in-flight HTTP requests. Defaults to DATABLUE_CONCURRENCY.

    Returns:
        List of {"fetch": <fetch_result>, "cb": <on_result return | None>} dicts,
        in completion order.

    Runs the asyncio loop inside a dedicated thread so it never collides with
    Celery/Django/gevent already-running loops.
    """
    api_key = _cfg("DATABLUE_API_KEY", "")
    if not api_key:
        logger.error("[DataBlue] DATABLUE_API_KEY not configured — fetch_many returning empty")
        return []
    if not items:
        return []

    conc = concurrency or _cfg("DATABLUE_CONCURRENCY", 100)
    timeout = _cfg("DATABLUE_TIMEOUT", 60)

    with _cf.ThreadPoolExecutor(max_workers=1) as outer_pool:
        return outer_pool.submit(
            asyncio.run,
            _pipeline_async(items, conc, api_key, timeout, on_result),
        ).result()


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
        resp = httpx.get(
            _api_url(),
            headers={"Authorization": f"Bearer {api_key}"},
            params=params,
            timeout=timeout,
        )
    except httpx.TimeoutException:
        logger.warning(f"[DataBlue] Timeout for '{keyword_text}'")
        return None
    except Exception as e:
        logger.warning(f"[DataBlue] Request failed for '{keyword_text}': {e}")
        return None

    if resp.status_code != 200:
        body_snippet = (resp.text or '')[:300].replace('\n', ' ')
        logger.warning(
            f"[DataBlue] Non-200 ({resp.status_code}) for '{keyword_text}': {body_snippet}"
        )
        return None

    try:
        raw = resp.json()
    except Exception as je:
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
