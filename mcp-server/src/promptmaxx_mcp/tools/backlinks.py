"""M8 — backlink profile (merged from the production branch 2026-08-24).

Read-only like everything else: the overview and item list are wrapped;
POST /seo/backlinks/fetch/ (which spends a DataForSEO call and hands a
snapshot to the engine) is not — trigger fetches from the UI. The engine
caps storage at 1,000 items per snapshot.
"""

from __future__ import annotations

from typing import Any

from ..client import PromptmaxxClient, guard_tool_errors


def register(mcp: Any, client: PromptmaxxClient) -> None:
    @mcp.tool()
    @guard_tool_errors
    def get_backlinks_overview(domain_id: int) -> dict:
        """Backlink profile overview for a client: current snapshot totals,
        history points, top anchors, top referring domains, top pages, and
        fetch state. Empty (snapshot: null) until a fetch has been run from
        the UI — fetching spends a DataForSEO call, so this tool never
        triggers one.
        """
        return client.get("/seo/backlinks/", params={"domain_id": domain_id})

    @mcp.tool()
    @guard_tool_errors
    def list_backlinks(
        domain_id: int,
        page: int = 1,
        sort: str = "",
    ) -> dict:
        """Individual backlinks from the latest snapshot for a client,
        50 per page. Optional sort: rank, domain_from_rank, page_from_rank,
        backlink_spam_score, first_seen, last_seen, domain_from.
        """
        params: dict[str, Any] = {"domain_id": domain_id, "page": max(1, page)}
        if sort:
            params["sort"] = sort
        return client.get("/seo/backlinks/list/", params=params)
