"""M2 — AI visibility: mentions, dashboard summary, share of voice,
sentiment, historical trends.

Publish-gate caveat (finding F14): the mentions endpoints serve only
is_published=True rows, while the dashboard summary counts every row.
The two can legitimately disagree when publication lags a measurement
sweep — stated on the affected tools.

/prompts/mentions/filters/ is deliberately not wrapped: it is
unauthenticated and computes across all tenants (finding F13).
/prompts/export/data/ is deliberately not wrapped: US-locale timestamps
and a 0..100 sentiment scale (findings F5, F6) — everything it offers is
available clean from the endpoints below.
"""

from __future__ import annotations

from typing import Any

from ..client import PromptmaxxClient
from ..normalize import normalize_mention, scrub_analytics


def register(mcp: Any, client: PromptmaxxClient) -> None:
    @mcp.tool()
    def list_mentions(
        domain_id: int,
        search: str = "",
        platform: str = "",
        sentiment: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """List AI-visibility mentions for a client: each row is one measured
        prompt/answer with platform, sentiment (scale -1..1), position,
        citations, competitor mentions, and an ISO 8601 timestamp.

        Filters: search (free text), platform (e.g. ChatGPT), sentiment
        (positive/neutral/negative). Pagination: limit (max 100) + offset;
        the response's total_count says how many rows match in all.

        Only published rows are served; the dashboard summary counts
        unpublished rows too, so its totals can exceed what is listed here
        (known inconsistency F14).
        """
        limit = max(1, min(limit, 100))
        result = client.get(
            "/prompts/mentions/",
            params={
                "domain_id": domain_id,
                "search": search,
                "platform": platform,
                "sentiment": sentiment,
                "limit": limit,
                "offset": max(0, offset),
            },
        )
        data = result["data"]
        if isinstance(data.get("mentions"), list):
            data["mentions"] = [
                normalize_mention(m) if isinstance(m, dict) else m
                for m in data["mentions"]
            ]
        # duplicated, unpaginated echo lists — noise next to the real rows
        data.pop("available_platforms", None)
        data.pop("available_sentiments", None)
        return result

    @mcp.tool()
    def get_mention(mention_id: int) -> dict:
        """Get one mention by id, with full citation objects and the complete
        answer description. Sentiment score is on the -1..1 scale.
        """
        result = client.get(f"/prompts/mentions/{mention_id}/")
        if isinstance(result["data"], dict):
            inner = result["data"].get("mention")
            if isinstance(inner, dict):
                result["data"]["mention"] = normalize_mention(inner)
            else:
                result["data"] = normalize_mention(result["data"])
        return result

    @mcp.tool()
    def get_visibility_summary(domain_id: int, days: int | None = None) -> dict:
        """The AI-visibility dashboard for a client: headline metrics
        (visibility score, mentions, citations), platform and country
        breakdowns, share of voice, and trend series. Optional days window.

        Two caveats. F4: the visibility_score here uses a different,
        unlabeled window than the one on the client record (get_client) —
        always say which endpoint a score came from. F14: these counts
        include unpublished rows, so totals can exceed list_mentions.
        Competitor names in the share-of-voice block are unreliable
        (extraction defect F2) — see get_share_of_voice.
        """
        params: dict[str, Any] = {"domain_id": domain_id}
        if days is not None:
            params["days"] = days
        result = client.get("/analytics/dashboard/summary/", params=params)
        result["data"] = scrub_analytics(result["data"])
        return result

    @mcp.tool()
    def get_share_of_voice(domain_id: int, days: int = 30) -> dict:
        """Share of voice for a client vs detected competitors over the last
        `days` days (default 30).

        Data quality warning (known defect F2): competitor names derive from
        cited URL hostnames, so the list includes publishers, tools, and
        unrelated brands (a live run for a stock broker returned a US TV
        network as top 'competitor'), while real rivals named in prose but
        never cited are missing. Do not present these as the client's market
        rivals without human review. Only the 'You' row is reliable.
        """
        result = client.get(
            "/analytics/share-of-voice/by_domain/",
            params={"domain_id": domain_id, "days": days},
        )
        data = scrub_analytics(result["data"])
        warning = (
            "Competitor names derive from cited hostnames and include "
            "publishers/non-competitors (known defect F2). Only the 'You' "
            "row is reliable."
        )
        if isinstance(data, list):
            result["data"] = {"brands": data, "data_quality_warning": warning}
        else:
            data["data_quality_warning"] = warning
            result["data"] = data
        return result

    @mcp.tool()
    def get_sentiment_summary(domain_id: int, days: int = 30) -> dict:
        """Sentiment analytics summary for a client over the last `days` days
        (default 30), with previous-period comparison.
        """
        result = client.get(
            "/analytics/sentiment-analytics/summary/",
            params={"domain_id": domain_id, "days": days},
        )
        result["data"] = scrub_analytics(result["data"])
        return result

    @mcp.tool()
    def get_historical_trends(
        domain_id: int,
        months: int = 12,
        start_date: str = "",
        end_date: str = "",
    ) -> dict:
        """Historical visibility trends for a client: monthly series of
        mention volumes and positions. Default window 12 months; narrow with
        months or an explicit start_date/end_date (YYYY-MM-DD).
        """
        params: dict[str, Any] = {"domain_id": domain_id, "months": months}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        result = client.get("/prompts/historical-trends/", params=params)
        result["data"] = scrub_analytics(result["data"])
        return result
