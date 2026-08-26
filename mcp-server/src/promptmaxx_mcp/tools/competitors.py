"""M3 — competitors and content gaps.

Every tool here carries a data_quality_warning, because the competitor set
these endpoints are computed from is known-bad (finding F2): names derive
from cited URL hostnames, so publishers, tools, and unrelated brands appear
as "competitors" while real rivals named in prose but never cited are
missing entirely.

get_competitive_insights is opt-in (PROMPTMAXX_MCP_ALLOW_INSIGHTS=1): the
endpoint turns the mis-extracted competitor set into ready-made narrative
sentences about the client's market position (finding F12) — prose designed
to be repeated, so it stays off by default.

Content gaps are computed on request from the analytics tables, not stored
rows — expect a slower response, and identical inputs recompute every call.
Gap responses come back camelCase (unlike the rest of the API); normalized
to snake_case here.
"""

from __future__ import annotations

from typing import Any

from ..client import PromptmaxxClient
from ..config import Config
from ..normalize import scrub_analytics, snake_keys

_WARNING = (
    "Competitor names in this data derive from cited URL hostnames and "
    "include publishers/non-competitors (known extraction defect F2); real "
    "rivals mentioned in prose but never cited are missing. Do not present "
    "these as the client's market rivals without human review."
)


def _clean(result: dict[str, Any]) -> dict[str, Any]:
    data = snake_keys(scrub_analytics(result["data"]))
    if isinstance(data, list):
        data = {"results": data}
    data["data_quality_warning"] = _WARNING
    result["data"] = data
    return result


def register(mcp: Any, client: PromptmaxxClient, config: Config) -> None:
    @mcp.tool()
    def list_content_gaps(
        domain_id: int,
        platform: str = "",
        priority: str = "",
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Content gaps for a client: prompts where competitors are covered
        but the client is not, with a summary block (totals by priority).
        Filters: platform, priority (high/medium/low). Paginated via
        page/page_size.

        Computed live from analytics on every call — slower than other
        tools, and each row's `id` is the underlying prompt id (stable).
        Data quality warning: the "competitors" driving these gaps are
        unreliable (defect F2) — treat gap topics as leads, not facts.
        """
        params: dict[str, Any] = {
            "domain_id": domain_id,
            "page": max(1, page),
            "page_size": max(1, min(page_size, 100)),
        }
        if platform:
            params["platform"] = platform
        if priority:
            params["priority"] = priority
        gaps = client.get("/competitors/content-gaps/", params=params)
        summary = client.get(
            "/competitors/content-gaps/summary/", params={"domain_id": domain_id}
        )
        combined = {
            "source_endpoint": gaps["source_endpoint"],
            "data": {
                "gaps": snake_keys(scrub_analytics(gaps["data"])),
                "summary": snake_keys(scrub_analytics(summary["data"])),
                "data_quality_warning": _WARNING,
            },
        }
        return combined

    @mcp.tool()
    def get_answer_gap_analysis(
        domain_id: int,
        competitor_id: int | None = None,
        platform: str = "",
    ) -> dict:
        """Answer-gap analysis for a client: prompts where a competitor is
        mentioned in AI answers and the client is not. Optionally narrow to
        one competitor_id or platform.

        Data quality warning: the competitor set is unreliable (defect F2).
        """
        params: dict[str, Any] = {"domain_id": domain_id}
        if competitor_id is not None:
            params["competitor_id"] = competitor_id
        if platform:
            params["platform"] = platform
        return _clean(client.get("/competitors/answer-gap-analysis/", params=params))

    @mcp.tool()
    def list_competitors(domain_id: int, platform: str = "") -> dict:
        """The detected competitor list for a client, with share-of-voice
        percentages, ordered by share.

        Data quality warning (defect F2): these names come from cited URL
        hostnames — on a live run for a stock broker the list contained a US
        TV network, publishers, and tools, while the real rivals were
        missing. Useful for auditing what the platform *thinks* the
        competitors are; not a source of truth about the market.
        """
        params: dict[str, Any] = {"domain_id": domain_id}
        if platform:
            params["platform"] = platform
        return _clean(client.get("/competitors/competitors/by_domain/", params=params))

    if config.allow_insights:
        @mcp.tool()
        def get_competitive_insights(domain_id: int, platform: str = "") -> dict:
            """Auto-generated competitive narrative for a client
            (opt-in via PROMPTMAXX_MCP_ALLOW_INSIGHTS=1).

            SEVERE data quality warning (defect F12): these are ready-made
            sentences built on the broken competitor extraction — a live
            instance produced "Amc leads with 42% share, 25% ahead of
            Zerodha", telling a stock broker it is losing to a US TV
            network. Never repeat these insights to a client or into a
            report; use them only to audit what the platform would claim.
            """
            params: dict[str, Any] = {"domain_id": domain_id}
            if platform:
                params["platform"] = platform
            result = _clean(client.get("/competitors/competitive-insights/", params=params))
            result["data"]["data_quality_warning"] = (
                "SEVERE (F12): auto-generated narrative built on mis-extracted "
                "competitors. Known-false statements about market position. "
                "Audit only — never repeat to a client or into a report."
            )
            return result
