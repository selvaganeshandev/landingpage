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
        resp = requests.post(
            DATABLUE_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
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
    return raw if organic else None
