"""M4 — SEO keyword tracking (activities 2, 8, and keyword-ranking reports).

Structures are live-confirmed against a real seeded keyword. Rank VALUES
stay 0 until the instance carries a DataBlue/DataForSEO credential and its
02:00 nightly scrape has run — an operational prerequisite of the instance,
not a defect. Tool descriptions say so, so empty rank data reads as
"not scraped yet", not "broken".
"""

from __future__ import annotations

from typing import Any

from ..client import PromptmaxxClient


def register(mcp: Any, client: PromptmaxxClient) -> None:
    @mcp.tool()
    def list_seo_keywords(domain_id: int) -> dict:
        """Tracked SEO keywords for a client, with current rank, rank deltas
        at 1/7/15/30-day horizons, target_url/crawl_url (the keyword-to-page
        mapping), favourite flag ("selected"), and tags.

        Rank fields are 0 until the instance has a DataBlue key and its
        nightly scrape has run. This list plus list_seo_opportunities is the
        keyword-ranking-report surface.
        """
        return client.get("/seo/keywords/", params={"domain_id": domain_id})

    @mcp.tool()
    def get_keyword_history(
        keyword_id: int, days: int = 30, offset: int = 0
    ) -> dict:
        """Rank history for one tracked keyword. `days` sets the window
        length; `offset` moves the window back (offset=0 is the trailing
        window, offset=days the one before it). Empty until rank scrapes
        have run on this instance.
        """
        return client.get(
            f"/seo/keywords/{keyword_id}/history/",
            params={"days": days, "offset": max(0, offset)},
        )

    @mcp.tool()
    def get_keyword_serp_features(keyword_id: int) -> dict:
        """SERP features observed for one tracked keyword (snippets, packs,
        etc.). Empty until rank scrapes have run on this instance.
        """
        return client.get(f"/seo/keywords/{keyword_id}/serp-features/")

    @mcp.tool()
    def get_keyword_volume(keyword_id: int) -> dict:
        """Search-volume record for one tracked keyword (volume, CPC,
        competition). Populated by the DataForSEO enrichment when the
        instance has credentials for it.
        """
        return client.get(f"/seo/keywords/{keyword_id}/volume/")

    @mcp.tool()
    def get_seo_overview(domain_id: int) -> dict:
        """SEO overview for a client: tracked keyword counts, rank
        distribution buckets, and movement summary.
        """
        return client.get("/seo/overview/", params={"domain_id": domain_id})

    @mcp.tool()
    def get_seo_metrics(domain_id: int, days: int = 30) -> dict:
        """SEO metrics for a client over the last `days` days (default 30):
        aggregate rank movement and visibility measures.
        """
        return client.get(
            "/seo/metrics/", params={"domain_id": domain_id, "days": days}
        )

    @mcp.tool()
    def list_seo_opportunities(domain_id: int) -> dict:
        """Keyword opportunities for a client, bucketed (ranking, top-three,
        not-ranked, with-volume, crawled). Returns zeros rather than failing
        when no SEO keywords are tracked yet.
        """
        return client.get("/seo/opportunities/", params={"domain_id": domain_id})
