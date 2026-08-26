"""Phase 4 smoke test: M4 SEO, M5 content, M7 keyword universe, M6 reports.

Usage: credentials via .env or environment, then
    python scripts/smoke_phase4.py
"""

import asyncio
import json
import sys

from promptmaxx_mcp.errors import readable_500
from promptmaxx_mcp.server import create_server

DOMAIN = 1
SEO_KEYWORD_ID = 1  # seeded during the integration audit
CONTENT_ID = 2      # generated during the integration audit
RUN_ID = 1          # generation run created during the integration audit

failures = 0


def ok(name, msg):
    print(f"PASS  {name:<26} {msg}")


def fail(name, msg):
    global failures
    failures += 1
    print(f"FAIL  {name:<26} {msg}")


def call(server, name, args, expect_keys=None, allow_error_contains=None):
    res = asyncio.run(server.call_tool(name, args))
    text = res.content[0].text if res.content else ""
    if res.is_error:
        if allow_error_contains and allow_error_contains in text:
            ok(name, f"expected readable error: {text[:70]}...")
        else:
            fail(name, text[:200])
        return None
    payload = json.loads(text)
    if expect_keys:
        data = payload["data"]
        missing = [k for k in expect_keys if isinstance(data, dict) and k not in data]
        if missing:
            fail(name, f"missing keys {missing}; got {list(data)[:8]}")
            return payload
    summary = (
        f"list[{len(payload['data'])}]" if isinstance(payload["data"], list)
        else str(list(payload["data"])[:5])
    )
    ok(name, f"{payload['source_endpoint']} -> {summary}")
    return payload


def main() -> int:
    server = create_server()

    # M4
    call(server, "list_seo_keywords", {"domain_id": DOMAIN})
    call(server, "get_keyword_history", {"keyword_id": SEO_KEYWORD_ID})
    call(server, "get_keyword_serp_features", {"keyword_id": SEO_KEYWORD_ID})
    call(server, "get_keyword_volume", {"keyword_id": SEO_KEYWORD_ID})
    call(server, "get_seo_overview", {"domain_id": DOMAIN})
    call(server, "get_seo_metrics", {"domain_id": DOMAIN})
    call(server, "list_seo_opportunities", {"domain_id": DOMAIN})

    # M5 (local instance has the columns — expect rows; on a fresh DB the
    # F1 mapping would fire instead)
    payload = call(server, "list_content", {"domain_id": DOMAIN})
    call(server, "get_content", {"content_id": CONTENT_ID})

    # M7
    payload = call(server, "list_keyword_universe", {"domain_id": DOMAIN},
                   expect_keys=["keywords", "total_count", "note"])
    if payload:
        rows = payload["data"]["keywords"]
        wrong = [r for r in rows if r.get("domain") != DOMAIN]
        if wrong:
            fail("universe_domain_filter", f"{len(wrong)} rows from other domains")
        elif rows:
            ok("universe_domain_filter", f"{len(rows)} rows, all domain {DOMAIN}")
        else:
            fail("universe_domain_filter", "0 rows — expected the 3 seeded")
    call(server, "get_active_generation_run", {"domain_id": DOMAIN})
    run = call(server, "get_generation_run", {"run_id": RUN_ID})
    if run:
        text = json.dumps(run)
        if "candidate" in text.lower():
            ok("generation_run_candidates", "candidates present in run detail")
        else:
            fail("generation_run_candidates", f"no candidates field: {list(run['data'])[:8]}")

    # M6
    call(server, "list_report_sheets", {"domain_id": DOMAIN})
    call(server, "get_report_sheet_data", {"domain_id": DOMAIN})

    # F1 mapping unit check
    msg = readable_500("/content/", 'column generated_contents.ai_detection_score does not exist')
    if msg and "F1" in msg and "0009" in msg:
        ok("f1_error_mapping", "signature maps to readable message")
    else:
        fail("f1_error_mapping", msg)

    # registry
    tools = sorted(t.name for t in asyncio.run(server.list_tools()))
    expected = 26  # 3+6+3+7+2+3+2, insights off
    if len(tools) == expected:
        ok("tool_registry", f"{len(tools)} tools (insights off)")
    else:
        fail("tool_registry", f"{len(tools)} tools, expected {expected}: {tools}")

    print(json.dumps({"failures": failures}))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
