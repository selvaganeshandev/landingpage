"""Collect live results for the ten integration activities via the MCP tool
layer, for the visualization report. Writes one JSON file."""

import asyncio
import json
import sys

from promptmaxx_mcp.server import create_server

OUT = sys.argv[1] if len(sys.argv) > 1 else "activities.json"

CALLS = {
    # activity key -> list of (tool, args)
    "1_content_gaps": [("list_content_gaps", {"domain_id": 1})],
    "2_keyword_mapping": [("list_seo_keywords", {"domain_id": 1}),
                           ("list_seo_keywords", {"domain_id": 2})],
    "3_keyword_research": [("list_keyword_universe", {"domain_id": 2}),
                            ("get_generation_run", {"run_id": 2})],
    "5_llm_optimization": [("get_site_health", {"domain_id": 2})],
    "6_blog_content": [("list_content", {"domain_id": 1}),
                        ("get_content", {"content_id": 2})],
    "8_rank_tracking": [("get_keyword_history", {"keyword_id": 3}),
                         ("get_keyword_volume", {"keyword_id": 3}),
                         ("get_seo_overview", {"domain_id": 2})],
    "9_ai_visibility": [("get_visibility_summary", {"domain_id": 1}),
                         ("list_mentions", {"domain_id": 1, "limit": 3}),
                         ("get_share_of_voice", {"domain_id": 1})],
    "10_ranking_reports": [("list_seo_opportunities", {"domain_id": 2}),
                            ("get_seo_metrics", {"domain_id": 2})],
    "4_backlinks": [("get_backlinks_overview", {"domain_id": 2})],
    "extra": [("get_content", {"content_id": 3}),
               ("list_seo_keywords", {"domain_id": 2}),
               ("get_sentiment_summary", {"domain_id": 1})],
}


def main():
    server = create_server()
    out = {}
    for activity, calls in CALLS.items():
        out[activity] = []
        for tool, args in calls:
            try:
                res = asyncio.run(server.call_tool(tool, args))
                text = res.content[0].text if res.content else ""
                payload = json.loads(text) if not res.is_error else {"error": text}
                out[activity].append({"tool": tool, "args": args,
                                      "ok": not res.is_error, "result": payload})
            except Exception as exc:  # noqa: BLE001
                out[activity].append({"tool": tool, "args": args,
                                      "ok": False, "result": {"error": str(exc)}})
            print(activity, tool, "ok" if out[activity][-1]["ok"] else "ERR")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
