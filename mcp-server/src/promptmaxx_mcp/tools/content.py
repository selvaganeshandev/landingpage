"""M5 — generated content (activities 6 and 7).

Hard dependency this server cannot fix (backend frozen): on any fresh
Promptmaxx database, GET /content/ 500s because migration content/0004 is
state-only and never created the AI-detection columns (finding F1). The
client maps that specific 500 to a readable error naming the defect; the
corrective migration (content/0009) exists locally but is uncommitted.
"""

from __future__ import annotations

from typing import Any

from ..client import PromptmaxxClient


def register(mcp: Any, client: PromptmaxxClient) -> None:
    @mcp.tool()
    def list_content(
        domain_id: int,
        status: str = "",
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Generated content artifacts for a client: planned, generated,
        rewritten and humanised articles (GeneratedContent rows), paginated
        via page/page_size. Optional status filter.

        Humanised rows preserve pre_humanise_content alongside the result.
        On an instance with the known F1 deployment defect this returns a
        readable error naming the missing columns instead of a stack trace.
        """
        params: dict[str, Any] = {
            "domain_id": domain_id,
            "page": max(1, page),
            "page_size": max(1, min(page_size, 100)),
        }
        if status:
            params["status"] = status
        return client.get("/content/", params=params)

    @mcp.tool()
    def get_content(content_id: int) -> dict:
        """One generated-content artifact by id, with full content_html,
        outline, AI-detection fields, and humanise state.
        """
        return client.get(f"/content/{content_id}/")
