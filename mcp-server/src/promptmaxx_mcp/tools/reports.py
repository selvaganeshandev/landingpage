"""M6 — organic report sheets (GSC/GA), optional surface.

The integration audit reclassified /seo/report-sheets/ away from keyword
ranking reports: its sheet types are all gsc_* and ga_* — the Organic
Reports module — and it holds data only when the instance has Google
Search Console / Analytics integrations connected. Wrapped honestly: an
empty result on an unconnected instance is expected, not an error.

Keyword-ranking reports live in M4 (list_seo_keywords +
list_seo_opportunities). The binary exports (xlsx/pdf) are not wrapped —
binary payloads don't belong in a context window.
"""

from __future__ import annotations

from typing import Any

from ..client import PromptmaxxClient, guard_tool_errors


def register(mcp: Any, client: PromptmaxxClient) -> None:
    @mcp.tool()
    @guard_tool_errors
    def list_report_sheets(domain_id: int) -> dict:
        """Configured organic report sheets for a client (GSC/GA sheet
        definitions). Empty unless the instance has Google Search Console /
        Analytics integrations connected — expected on most instances.
        """
        return client.get("/seo/report-sheets/", params={"domain_id": domain_id})

    @mcp.tool()
    @guard_tool_errors
    def get_report_sheet_data(domain_id: int) -> dict:
        """Live data for every configured organic report sheet of a client
        (GSC/GA metrics). Returns `reports: 0`-style emptiness when no
        sheets are configured or Google integrations are absent — expected,
        not an error.
        """
        return client.get("/seo/report-sheets/data/", params={"domain_id": domain_id})
