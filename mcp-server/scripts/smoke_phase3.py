"""Phase 3 smoke test: M3 competitor tools — warnings, snake_case, gating.

Usage: credentials via .env or environment, then
    python scripts/smoke_phase3.py
"""

import asyncio
import json
import os
import sys

from promptmaxx_mcp.server import create_server

DOMAIN = 1


def call(server, name, args):
    res = asyncio.run(server.call_tool(name, args))
    text = res.content[0].text if res.content else ""
    return res.is_error, text


def main() -> int:
    failures = 0

    def ok(name, msg):
        print(f"PASS  {name:<26} {msg}")

    def fail(name, msg):
        nonlocal failures
        failures += 1
        print(f"FAIL  {name:<26} {msg}")

    os.environ.pop("PROMPTMAXX_MCP_ALLOW_INSIGHTS", None)
    server = create_server()
    tools = sorted(t.name for t in asyncio.run(server.list_tools()))

    # gating: insights absent by default
    if "get_competitive_insights" not in tools:
        ok("insights_gated_off", "tool absent with flag unset")
    else:
        fail("insights_gated_off", "tool registered without flag")

    # content gaps: combined gaps+summary, warning, snake_case keys
    err, text = call(server, "list_content_gaps", {"domain_id": DOMAIN})
    if err:
        fail("list_content_gaps", text[:200])
    else:
        payload = json.loads(text)["data"]
        has_all = all(k in payload for k in ("gaps", "summary", "data_quality_warning"))
        if has_all:
            ok("list_content_gaps", "gaps + summary + warning present")
        else:
            fail("list_content_gaps", f"keys: {list(payload)}")
        camel = [k for k in json.dumps(payload).split('"') if k[:1].islower() and any(c.isupper() for c in k) and " " not in k]
        if camel:
            fail("gaps_snake_case", f"camelCase keys survived: {sorted(set(camel))[:6]}")
        else:
            ok("gaps_snake_case", "no camelCase keys in response")

    # answer gaps
    err, text = call(server, "get_answer_gap_analysis", {"domain_id": DOMAIN})
    if err:
        fail("get_answer_gap_analysis", text[:200])
    elif "data_quality_warning" in text:
        ok("get_answer_gap_analysis", "responds with warning")
    else:
        fail("get_answer_gap_analysis", "warning missing")

    # competitors list
    err, text = call(server, "list_competitors", {"domain_id": DOMAIN})
    if err:
        fail("list_competitors", text[:200])
    elif "data_quality_warning" in text:
        ok("list_competitors", "responds with warning")
    else:
        fail("list_competitors", "warning missing")

    # gating: insights present with flag, SEVERE warning attached
    os.environ["PROMPTMAXX_MCP_ALLOW_INSIGHTS"] = "1"
    server_on = create_server()
    tools_on = sorted(t.name for t in asyncio.run(server_on.list_tools()))
    if "get_competitive_insights" in tools_on:
        err, text = call(server_on, "get_competitive_insights", {"domain_id": DOMAIN})
        if err:
            fail("insights_flag_on", text[:200])
        elif "SEVERE" in text:
            ok("insights_flag_on", "registered with flag; SEVERE warning attached")
        else:
            fail("insights_flag_on", "SEVERE warning missing")
    else:
        fail("insights_flag_on", "tool absent despite flag")
    os.environ.pop("PROMPTMAXX_MCP_ALLOW_INSIGHTS", None)

    expected = 12  # 3 M1 + 6 M2 + 3 M3 (insights off)
    if len(tools) == expected:
        ok("tool_registry", f"{len(tools)} tools (insights off)")
    else:
        fail("tool_registry", f"{len(tools)} tools, expected {expected}: {tools}")

    print(json.dumps({"failures": failures}))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
