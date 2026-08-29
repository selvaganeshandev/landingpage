"""M7 — the AI-generated keyword universe and prompt generation runs
(activity 3, keyword research).

Two persisted lanes exist. Lane 1: onboarding writes the generated keyword
universe to the Keyword table. Lane 2: prompt generation runs persist a
draft-review lifecycle (PromptGenerationRun + PromptCandidate).

Known limits, stated rather than papered over: /keywords/ has NO
server-side domain filter (it returns everything the credential can see),
so this module filters by domain client-side; SecondaryKeyword (unselected
manual-flow keywords) has no read endpoint at all; and the outputs of
generate-semantic-keywords / suggest-keywords are never persisted (finding
F10) — that work is unreachable by any read.
"""

from __future__ import annotations

from typing import Any

from ..client import PromptmaxxClient, guard_tool_errors


def register(mcp: Any, client: PromptmaxxClient) -> None:
    @mcp.tool()
    @guard_tool_errors
    def list_keyword_universe(domain_id: int) -> dict:
        """The AI-generated keyword universe for a client (Keyword table):
        keyword text, intent, volume level, entity, topic, cluster, source
        (e.g. ai-generated), and modified_at.

        Filtered server-side by domain_id. Enrichment fields (intent,
        volume) are null until the corresponding pipelines have run.
        """
        result = client.get("/keywords/", params={"domain_id": domain_id})
        data = result["data"]
        rows = data if isinstance(data, list) else data.get("keywords", [])
        # Belt and braces: re-filter locally so an older backend without the
        # server-side domain filter still returns correct (if slower) data.
        filtered = [
            row for row in rows
            if isinstance(row, dict) and row.get("domain") == domain_id
        ]
        result["data"] = {
            "keywords": filtered,
            "total_count": len(filtered),
        }
        return result

    @mcp.tool()
    @guard_tool_errors
    def get_active_generation_run(domain_id: int) -> dict:
        """The currently active prompt generation run for a client, if any —
        a stored draft-review lifecycle whose candidates await accept or
        discard.
        """
        return client.get(
            "/prompts/generation-runs/active/", params={"domain_id": domain_id}
        )

    @mcp.tool()
    @guard_tool_errors
    def get_generation_run(run_id: int) -> dict:
        """One prompt generation run by id, with its stored candidates —
        e.g. raw search queries rewritten into question-style prompt
        candidates, each carrying its accept/discard status.
        """
        return client.get(f"/prompts/generation-runs/{run_id}/")
