"""
DataBlue web-scrape client — second-opinion link checking.

Why this exists
---------------
`LinkValidator` decides "is this cited page alive?" with a bare `requests.head()`
sent under a bot User-Agent. That is free and right most of the time, but it is
also the reason ~1,400 of the 9,773 rows currently recorded as "failed" are not
actually broken:

  * 403 (1,145 rows) — Cloudflare and friends reject the bot UA outright. The
    page is fine; we were simply turned away at the door.
  * 429 (154 rows)   — we asked too fast. That is our problem, not the page's.
  * 202 and similar  — success codes that fell into the catch-all "broken" arm.

A real scraper gets past exactly those cases, so DataBlue is used as an *appeal*,
not as the first check: the cheap HEAD still runs on every URL, and only an
inconclusive verdict escalates here. On the current data that is roughly one
paid call per seven URLs instead of one per URL.

Endpoint contract
-----------------
`POST /v1/scrape` with `{"url": "..."}`. There is no published `/docs`, so the
shape below was established by probing the live endpoint:

    {"success": true,
     "data": {"markdown":  "...",
              "status":    "success" | "thin" | "blocked",
              "quality":   {"markdown_len": 4052, ...},
              "metadata":  {"status_code": 200, "title": ..., ...},
              "empty_reason": null,
              "time_taken": 1.478}}

The trap: **`success` is true even for a dead page.** It reports whether the
scrape ran, not whether the page is alive — a 404 comes back `success: true`
with the site's error page rendered into `markdown`. Likewise `data.status` is
DataBlue's own quality verdict, not an HTTP result.

The only field that answers our question is `data.metadata.status_code`, the
origin's real HTTP status. Observed values:

    https://www.acra.gov.sg                 → 200  (live)
    https://github.com/<missing-repo>       → 404  (genuinely broken)
    https://httpbin.org/status/404          → 503  (origin itself failing)
    https://nonexistent-domain-xyz.com      → 0    (never reached)

`0` means DataBlue could not reach the host either, which is not proof the page
is broken — that resolves to *inconclusive* so the caller keeps its own verdict.
"""
import logging
from typing import Optional, Tuple

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_SCRAPE_URL = "https://api.datablue.dev/v1/scrape"

# Keys under data.metadata that carry the origin's HTTP status, best first.
# status_code is what DataBlue actually returns; the rest are defensive.
_STATUS_KEYS = ("status_code", "http_status_code", "http_status", "statusCode")

# Keys under data that carry the fetched page body. markdown is what DataBlue
# returns today; html/content/text cover a format change.
_CONTENT_KEYS = ("markdown", "html", "content", "body", "text")

# Verdict returned when we cannot tell. Distinct from False, which asserts
# "this link is broken" — a distinction the caller depends on.
INCONCLUSIVE = None


def _cfg(name: str, default):
    return getattr(settings, name, default)


def is_enabled() -> bool:
    """True when the fallback is switched on and a key is present.

    Checked before every escalation so a missing key degrades to today's
    behaviour instead of raising.
    """
    return bool(_cfg("MISINFO_DATABLUE_FALLBACK", True)) and bool(_cfg("DATABLUE_API_KEY", ""))


def _extract_status(metadata: dict) -> Optional[int]:
    """Pull the origin's HTTP status out of data.metadata, if present.

    Returns None for a missing/unparseable value and for 0, which DataBlue uses
    to mean "never reached the host" — that is an absence of information, not a
    status, and must not be compared against 400.
    """
    for key in _STATUS_KEYS:
        raw = metadata.get(key)
        if raw is None:
            continue
        try:
            code = int(raw)
        except (TypeError, ValueError):
            continue
        if 100 <= code <= 599:
            return code
    return None


def _extract_content(data: dict) -> str:
    """Pull the page body out of the data object."""
    for key in _CONTENT_KEYS:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _interpret(payload: dict) -> Tuple[Optional[bool], Optional[int], Optional[str]]:
    """Turn a DataBlue response into (verdict, status_code, error).

    `data.metadata.status_code` decides it whenever present. Body content is only
    consulted as a last resort, and deliberately never overrides a status — a
    scraper happily renders a 404 page, and that page is still a 404.
    """
    if not isinstance(payload, dict):
        return INCONCLUSIVE, None, "unreadable response"

    # success=false means the API call itself failed — tells us about DataBlue,
    # not about the page. (success=true says nothing either way; see module doc.)
    if payload.get("success") is False:
        detail = payload.get("error") or payload.get("detail") or "scrape failed"
        return INCONCLUSIVE, None, str(detail)

    # Tolerate the payload being flattened in a future version.
    data = payload.get("data")
    if not isinstance(data, dict):
        data = payload
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    status_code = _extract_status(metadata)
    if status_code is not None:
        if 200 <= status_code < 400:
            return True, status_code, None
        return False, status_code, f"HTTP {status_code}"

    # No usable status. 'blocked' means DataBlue was stopped too — our HEAD
    # already failed, so nothing here adds information.
    if data.get("status") == "blocked" or data.get("empty_reason"):
        return INCONCLUSIVE, None, f"datablue blocked ({data.get('empty_reason') or 'blocked'})"

    # Real content and no contrary status: the page served something.
    if _extract_content(data):
        return True, 200, None

    return INCONCLUSIVE, None, "no status or content in response"


def check_url(url: str) -> Tuple[Optional[bool], Optional[int], Optional[str]]:
    """Ask DataBlue whether `url` actually loads.

    Returns (verdict, status_code, error):
      * (True,  code, None)   — the page loads
      * (False, code, msg)    — the page is genuinely broken
      * (None,  None, msg)    — inconclusive; caller must keep its own verdict

    Never raises. Every failure path collapses to inconclusive, because this runs
    inside a scan loop over thousands of URLs where one bad response must not
    abort the run.
    """
    if not is_enabled():
        return INCONCLUSIVE, None, "datablue fallback disabled or key missing"

    api_key = _cfg("DATABLUE_API_KEY", "")
    endpoint = _cfg("DATABLUE_SCRAPE_URL", DEFAULT_SCRAPE_URL)
    timeout = _cfg("DATABLUE_SCRAPE_TIMEOUT", 30)

    # Field name is configurable: the request schema is unpublished, so if the
    # endpoint expects something other than {"url": ...} it can be corrected in
    # settings without a code change.
    body = {_cfg("DATABLUE_SCRAPE_URL_FIELD", "url"): url}
    extra = _cfg("DATABLUE_SCRAPE_EXTRA", None)
    if isinstance(extra, dict):
        body.update(extra)

    try:
        resp = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=timeout,
        )
    except requests.Timeout:
        logger.warning(f"[DataBlue scrape] timeout for {url}")
        return INCONCLUSIVE, None, "datablue timeout"
    except requests.RequestException as e:
        logger.warning(f"[DataBlue scrape] request failed for {url}: {e}")
        return INCONCLUSIVE, None, f"datablue request failed: {e}"

    # 401/403 here is DataBlue rejecting *us* (bad or expired key), which says
    # nothing about the cited page. Logged loudly because it disables the whole
    # fallback silently otherwise.
    if resp.status_code in (401, 403):
        logger.error(
            f"[DataBlue scrape] auth rejected ({resp.status_code}) — check DATABLUE_API_KEY"
        )
        return INCONCLUSIVE, None, "datablue auth rejected"

    if resp.status_code != 200:
        logger.warning(f"[DataBlue scrape] non-200 ({resp.status_code}) for {url}")
        return INCONCLUSIVE, None, f"datablue HTTP {resp.status_code}"

    try:
        payload = resp.json()
    except ValueError:
        return INCONCLUSIVE, None, "datablue returned non-JSON"

    return _interpret(payload)
