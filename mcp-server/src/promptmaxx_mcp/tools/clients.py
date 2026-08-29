"""M1 — clients (domains) and the site-health audit."""

from __future__ import annotations

from typing import Any

from ..client import PromptmaxxClient, guard_tool_errors


def register(mcp: Any, client: PromptmaxxClient) -> None:
    @mcp.tool()
    @guard_tool_errors
    def list_clients() -> dict:
        """List every client (domain) visible to this credential.

        Each row's `id` is the domain_id that every other tool requires.
        Start here to find the client you want to query.
        """
        return client.get("/domains/")

    @mcp.tool()
    @guard_tool_errors
    def get_client(domain_id: int) -> dict:
        """Get one client (domain) record by id.

        Caveat (known defect F4): the `visibility_score` on this record uses a
        different, unlabeled time window than the dashboard summary's — the two
        legitimately disagree (e.g. 81.83 vs 61.65 for the same client at the
        same moment). Always name the source endpoint when quoting the score.
        """
        return client.get(f"/domains/{domain_id}/")

    @mcp.tool()
    @guard_tool_errors
    def get_site_health(domain_id: int) -> dict:
        """Run the site-health audit for a client's website.

        Checks llms.txt presence, robots.txt, Schema.org structured-data
        blocks, and XML/HTML sitemaps, with scores per check. Results are
        stored server-side in DomainHealthCheck with history.

        Slow: this performs a live crawl of the client's site (typically
        several seconds), not a cached read. Call it when asked about
        AI-readiness or llms.txt, not routinely.
        """
        return client.get(f"/domains/{domain_id}/health-check/", timeout=120.0)
