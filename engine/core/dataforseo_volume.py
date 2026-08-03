"""
DataForSEO keyword search-volume client.

Google search volume for tracked keywords. DataBlue supplies rankings but no
volume at any `advanced` setting, so before this the figure was blank on 91% of
keywords and the Volume History tab was hidden.

Endpoint: POST /v3/keywords_data/google_ads/search_volume/live

Pricing drives the whole design here: the call is billed **per request, not per
keyword** ($0.09 flat), and accepts up to 1,000 keywords. Verified empirically —
requests of 2, 20 and 200 keywords all cost exactly $0.09. So the cost of this
integration is set by how many *requests* we make, and a request must be
batched as fully as possible.

A request carries one location_code and one language_code, so keywords can only
share a call when they share both. That makes the batching key
(location, language) and the cost formula:

    sum over each (location, language) group of ceil(group_size / 1000) * $0.09

At current volume — 2,218 in/en, 910 us/en, 12 sg/en — that is 3 + 1 + 1 = 5
requests, about $0.45 to refresh every keyword the system tracks.
"""
import logging
import math
from typing import Dict, Iterable, List, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

LIVE_URL = "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"
SANDBOX_URL = "https://sandbox.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"

# DataForSEO's hard cap for one search_volume request.
MAX_KEYWORDS_PER_REQUEST = 1000

# Flat price per request, for cost reporting only — the API bills whatever it
# bills; this just lets the command print an estimate before spending money.
COST_PER_REQUEST = 0.09

# Country ISO-3166-alpha-2 -> DataForSEO location_code, for the countries in
# use. Anything not listed falls back to LOCATION_FALLBACK so a keyword with an
# unmapped region still gets a figure rather than being skipped silently; the
# caller logs the substitution.
ISO_TO_LOCATION_CODE = {
    "us": 2840, "in": 2356, "gb": 2826, "uk": 2826, "au": 2036, "ca": 2124,
    "sg": 2702, "ae": 2784, "de": 2276, "fr": 2250, "es": 2724, "it": 2380,
    "nl": 2528, "br": 2076, "mx": 2484, "jp": 2392, "kr": 2410, "cn": 2156,
    "id": 2360, "my": 2458, "ph": 2608, "th": 2764, "vn": 2704, "za": 2710,
    "ng": 2566, "ke": 2404, "eg": 2818, "sa": 2682, "pk": 2586, "bd": 2050,
    "lk": 2144, "np": 2524, "nz": 2554, "ie": 2372, "se": 2752, "no": 2578,
    "dk": 2208, "fi": 2246, "pl": 2616, "pt": 2620, "gr": 2300, "tr": 2792,
    "ru": 2643, "ua": 2804, "ar": 2032, "cl": 2152, "co": 2170, "pe": 2604,
    "ch": 2756, "at": 2040, "be": 2056, "cz": 2203, "hu": 2348, "ro": 2642,
    "il": 2376, "hk": 2344, "tw": 2158,
}
LOCATION_FALLBACK = 2840  # United States

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class DataForSeoError(RuntimeError):
    """Raised when the API is unreachable or returns a non-success status."""


def _credentials():
    login = getattr(settings, "DATAFORSEO_LOGIN", None)
    password = getattr(settings, "DATAFORSEO_PASSWORD", None)
    if not login or not password:
        raise DataForSeoError(
            "DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD are not configured. "
            "Set them in the engine .env."
        )
    return login, password


def _url():
    if getattr(settings, "DATAFORSEO_USE_SANDBOX", False):
        return SANDBOX_URL
    return LIVE_URL


def location_code_for(isocode: str) -> int:
    """Map a keyword's two-letter region to a DataForSEO location code."""
    code = ISO_TO_LOCATION_CODE.get((isocode or "").strip().lower())
    if code:
        return code
    logger.warning(
        "No DataForSEO location for isocode %r — falling back to US (%s). "
        "Volume for these keywords reflects US search, not their own market.",
        isocode, LOCATION_FALLBACK,
    )
    return LOCATION_FALLBACK


def estimate_requests(group_sizes: Iterable[int]) -> int:
    """Requests needed for the given per-(location,language) group sizes."""
    return sum(math.ceil(n / MAX_KEYWORDS_PER_REQUEST) for n in group_sizes if n)


def fetch_search_volume(
    keywords: List[str],
    location_code: int,
    language_code: str = "en",
    timeout: int = 180,
) -> Dict[str, dict]:
    """Fetch volume for up to MAX_KEYWORDS_PER_REQUEST keywords in one call.

    Returns {lowercased keyword: parsed dict}. Keywords Google has no data for
    come back with search_volume None; those are returned too so the caller can
    tell "no data" apart from "not requested" and avoid re-requesting them
    every sweep.
    """
    if not keywords:
        return {}
    if len(keywords) > MAX_KEYWORDS_PER_REQUEST:
        raise ValueError(
            f"{len(keywords)} keywords exceeds the {MAX_KEYWORDS_PER_REQUEST} "
            "per-request cap — batch before calling."
        )

    payload = [{
        "keywords": keywords,
        "location_code": location_code,
        "language_code": language_code,
    }]

    try:
        resp = requests.post(
            _url(), auth=_credentials(), json=payload, timeout=timeout,
        )
    except requests.RequestException as exc:
        raise DataForSeoError(f"DataForSEO request failed: {exc}") from exc

    if resp.status_code != 200:
        raise DataForSeoError(
            f"DataForSEO HTTP {resp.status_code}: {resp.text[:300]}"
        )

    try:
        body = resp.json()
    except ValueError as exc:
        raise DataForSeoError(f"DataForSEO returned non-JSON: {resp.text[:300]}") from exc

    # 20000 is DataForSEO's success code; anything else is an API-level error
    # even though the HTTP status was 200.
    if body.get("status_code") != 20000:
        raise DataForSeoError(
            f"DataForSEO status {body.get('status_code')}: {body.get('status_message')}"
        )

    tasks = body.get("tasks") or []
    if not tasks:
        return {}
    task = tasks[0]
    if task.get("status_code") != 20000:
        raise DataForSeoError(
            f"DataForSEO task {task.get('status_code')}: {task.get('status_message')}"
        )

    out: Dict[str, dict] = {}
    for item in (task.get("result") or []):
        kw = (item.get("keyword") or "").strip()
        if kw:
            out[kw.lower()] = _parse_result(item)
    return out


def _parse_result(item: dict) -> dict:
    """Normalise one API result into the shape SeoKeywordVolume stores."""
    monthly = item.get("monthly_searches") or []

    # DataForSEO returns newest month first. Reverse to chronological so the
    # Volume History chart reads left-to-right like every other time series.
    ordered = list(reversed(monthly))
    volumes, labels = [], []
    for m in ordered:
        vol = m.get("search_volume")
        volumes.append(int(vol) if vol is not None else 0)
        month = m.get("month")
        name = MONTH_NAMES[month - 1] if isinstance(month, int) and 1 <= month <= 12 else "?"
        labels.append(name)

    avg = item.get("search_volume")
    comp_index = item.get("competition_index")

    return {
        "average_volume": int(avg) if avg is not None else 0,
        # Derived from the series, not returned by the API.
        "top_volume": max(volumes) if volumes else 0,
        "low_volume": min(volumes) if volumes else 0,
        "comp_level": (item.get("competition") or "-") or "-",
        "comp_index": str(comp_index) if comp_index is not None else "-",
        "month_wise_volume": volumes,
        "month_labels": labels,
        # Google genuinely has no volume for this term, as opposed to us not
        # having asked. Recorded so the sweeper stops retrying it.
        "no_data": avg is None,
    }
