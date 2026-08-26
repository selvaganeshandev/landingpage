"""Phase 2 smoke test: M2 visibility tools + normalization guarantees.

Usage: credentials via .env or environment, then
    python scripts/smoke_phase2.py
"""

import asyncio
import json
import sys

from promptmaxx_mcp.client import PromptmaxxClient, PromptmaxxError
from promptmaxx_mcp.config import load_config
from promptmaxx_mcp.normalize import MENTION_DROP_FIELDS, snake_keys
from promptmaxx_mcp.server import create_server

DOMAIN = 1


def main() -> int:
    config = load_config()
    client = PromptmaxxClient(config)
    failures = 0

    def fail(name, msg):
        nonlocal failures
        failures += 1
        print(f"FAIL  {name:<24} {msg}")

    def ok(name, msg):
        print(f"PASS  {name:<24} {msg}")

    # -- list_mentions normalization ---------------------------------------
    try:
        r = client.get("/prompts/mentions/", params={"domain_id": DOMAIN, "limit": 50, "offset": 0})
        rows = r["data"]["mentions"]
        from promptmaxx_mcp.normalize import normalize_mention
        rows = [normalize_mention(m) for m in rows]
        if not rows:
            fail("list_mentions", "no rows returned")
        else:
            leaked = MENTION_DROP_FIELDS & set(rows[0])
            if leaked:
                fail("mentions_drop_fields", f"dropped fields leaked: {leaked}")
            else:
                ok("mentions_drop_fields", f"{len(rows)} rows, none of the {len(MENTION_DROP_FIELDS)} display fields")
            if rows[0].get("sentiment_scale") == "-1..1":
                ok("sentiment_scale", "tagged -1..1")
            else:
                fail("sentiment_scale", f"missing/wrong: {rows[0].get('sentiment_scale')}")
            ts = rows[0].get("timestamp", "")
            if "T" in ts and ("+" in ts or ts.endswith("Z")):
                ok("iso_timestamp", ts)
            else:
                fail("iso_timestamp", f"not ISO: {ts}")
            expected_keeps = {"id", "platform", "mention_text_long", "description",
                              "sentiment", "sentiment_score", "position", "timestamp",
                              "group_id", "citations_count", "competitor_mentions"}
            missing = expected_keeps - set(rows[0])
            if missing:
                fail("mentions_keep_fields", f"missing keep fields: {missing}")
            else:
                ok("mentions_keep_fields", "all keep fields present")
    except PromptmaxxError as exc:
        fail("list_mentions", exc)

    # -- live endpoints through the client ---------------------------------
    from promptmaxx_mcp.normalize import scrub_analytics

    def live(name, path, params=None):
        try:
            r = client.get(path, params=params)
            r["data"] = scrub_analytics(r["data"])
            if json.dumps(r["data"]).find('"color"') >= 0:
                fail(name, "tailwind color field survived scrub")
            else:
                keys = list(r["data"])[:6] if isinstance(r["data"], dict) else f"list[{len(r['data'])}]"
                ok(name, f"{path} -> {keys}")
        except PromptmaxxError as exc:
            fail(name, exc)

    live("summary", "/analytics/dashboard/summary/", {"domain_id": DOMAIN})
    live("share_of_voice", "/analytics/share-of-voice/by_domain/", {"domain_id": DOMAIN, "days": 30})
    live("sentiment_summary", "/analytics/sentiment-analytics/summary/", {"domain_id": DOMAIN, "days": 30})
    live("historical_trends", "/prompts/historical-trends/", {"domain_id": DOMAIN, "months": 12})
    live("get_mention", "/prompts/mentions/6/")

    # -- pure normalization units ------------------------------------------
    converted = snake_keys({"currentCoverage": 1, "nested": [{"competitorMentions": 2}]})
    if converted == {"current_coverage": 1, "nested": [{"competitor_mentions": 2}]}:
        ok("snake_keys", "camelCase converted recursively")
    else:
        fail("snake_keys", converted)

    # -- registry ----------------------------------------------------------
    server = create_server()
    tools = sorted(t.name for t in asyncio.run(server.list_tools()))
    expected = sorted([
        "get_client", "get_site_health", "list_clients",
        "list_mentions", "get_mention", "get_visibility_summary",
        "get_share_of_voice", "get_sentiment_summary", "get_historical_trends",
    ])
    if tools == expected:
        ok("tool_registry", f"{len(tools)} tools")
    else:
        fail("tool_registry", f"got {tools}")

    client.close()
    print(json.dumps({"failures": failures}))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
