"""Client-side normalization of Promptmaxx API responses.

The backend is frozen: every contract defect the integration audit found
(findings F5-F7) is absorbed here instead of fixed at the source. One
shared layer so a future versioned export surface can replace it wholesale.

What it does:
- strips display-only fields the API leaks into data responses (F7),
  including fields that are unimplemented and always zero;
- tags sentiment scores with their scale, because the API serves the same
  value as -1..1 on one endpoint and 0..100 on another with no field
  naming either (F5) — this server only wraps the -1..1 endpoints;
- converts camelCase keys to snake_case where one module (content gaps)
  deviates from the API's otherwise snake_case convention.
"""

from __future__ import annotations

import re
from typing import Any

# Display/unimplemented fields on mention records (F7, F11). domain_name and
# domain_url are redundant: the caller already picked the client.
MENTION_DROP_FIELDS = frozenset({
    "mention_text_short",
    "time_ago",
    "rank",
    "domain_name",
    "domain_url",
    "views",
    "shares",
    "engagement_score",
    "key_topics",
})

# Presentation fields served inside analytics blocks (F7): Tailwind class
# names in the countries breakdown.
ANALYTICS_DROP_FIELDS = frozenset({"color"})

SENTIMENT_SCALE = "-1..1"


def strip_fields(record: dict[str, Any], drop: frozenset[str]) -> dict[str, Any]:
    return {k: v for k, v in record.items() if k not in drop}


def normalize_mention(record: dict[str, Any]) -> dict[str, Any]:
    """One mention row: drop display fields, name the sentiment scale."""
    cleaned = strip_fields(record, MENTION_DROP_FIELDS)
    if "sentiment_score" in cleaned:
        cleaned["sentiment_scale"] = SENTIMENT_SCALE
    return cleaned


def scrub_analytics(value: Any) -> Any:
    """Recursively remove presentation fields from an analytics payload."""
    if isinstance(value, dict):
        return {
            k: scrub_analytics(v)
            for k, v in value.items()
            if k not in ANALYTICS_DROP_FIELDS
        }
    if isinstance(value, list):
        return [scrub_analytics(item) for item in value]
    return value


_CAMEL = re.compile(r"(?<=[a-z0-9])([A-Z])")


def snake_keys(value: Any) -> Any:
    """Recursively convert camelCase dict keys to snake_case."""
    if isinstance(value, dict):
        return {
            _CAMEL.sub(lambda m: "_" + m.group(1).lower(), k): snake_keys(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [snake_keys(item) for item in value]
    return value
