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

DATABLUE_API_URL = "https://api.datablue.dev/v1/data/google/search"


def _cfg(name: str, default):
    return getattr(settings, name, default)


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


def _build_payload(keyword_text: str, isocode: str, language_code: str) -> dict:
    payload = {
        "query": (keyword_text or "")[:256],
        "num_results": _cfg("DATABLUE_NUM_RESULTS", 50),
    }
    if language_code:
        payload["language"] = language_code
    if isocode:
        payload["country"] = str(isocode).lower()
    return payload


# ---------------------------------------------------------------------------
# ASYNC LAYER — used by fetch_many
# ---------------------------------------------------------------------------
async def _fetch_one_async(client, sem, item_id, item_data, api_key, timeout):
    """Single DataBlue request, concurrency-limited by semaphore."""
    payload = _build_payload(
        item_data.get("keyword", ""),
        item_data.get("isocode", ""),
        item_data.get("language_code") or item_data.get("language", ""),
    )

    async with sem:
        try:
            resp = await client.post(
                DATABLUE_API_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
                timeout=timeout,
            )
            if resp.status_code == 200:
                try:
                    raw = resp.json()
                    organic = raw.get("organic_results", []) or []
                    raw["organic_results"] = _normalize_organic(organic)
                    # Trust DataBlue's own success flag. An empty organic list
                    # with success=true is a legitimate "not in top N" — let
                    # the parser record rank=0 instead of flagging the keyword
                    # as failed (which would skip it until tomorrow's
                    # scheduler retry). Fall back to True if the field is
                    # absent so we don't regress on schema changes.
                    api_success = bool(raw.get("success", True))
                    return {
                        "item_id": item_id,
                        "status": resp.status_code,
                        "data": raw,
                        "success": api_success,
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
                f"kw={payload.get('query', '')[:60]} body={body_snippet}"
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


def fetch_one(keyword_text: str, isocode: str = "", language_code: str = "") -> Optional[dict]:
    """Sync single-keyword DataBlue call.

    Returns the parsed JSON response (with normalized organic_results) or None
    on any failure (no key, non-200, timeout, JSON parse error, empty results).
    """
    api_key = _cfg("DATABLUE_API_KEY", "")
    if not api_key:
        logger.error("[DataBlue] DATABLUE_API_KEY not configured")
        return None

    payload = _build_payload(keyword_text, isocode, language_code)
    timeout = _cfg("DATABLUE_TIMEOUT", 60)

    try:
        resp = httpx.post(
            DATABLUE_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
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
    # Trust DataBlue's success flag. success=false → DataBlue couldn't fetch
    # (should be retried). success=true with empty organic → legitimate "not
    # ranked in top N" → return raw so the parser records rank=0 and the
    # keyword is marked 'done' rather than 'fail'.
    if not raw.get("success", True):
        return None
    return raw
