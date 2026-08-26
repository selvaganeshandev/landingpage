"""Full contract check: call every registered tool live and print a table.

The backend ships no OpenAPI spec and no contract (finding F9), so this
script IS the contract check — run it after any Promptmaxx update to catch
API drift before Claude does.

Usage: credentials via .env or environment, then
    python scripts/smoke.py

Exercises all tools including the gated insights tool (the flag is forced
on for the duration of the check).
"""

import asyncio
import json
import os
import sys
import time

from promptmaxx_mcp.server import create_server

# ids seeded/created during the 2026-08 integration audit of the local
# instance; adjust per instance if needed
DEFAULT_ARGS = {
    "domain_id": int(os.environ.get("SMOKE_DOMAIN_ID", 1)),
    "keyword_id": int(os.environ.get("SMOKE_KEYWORD_ID", 1)),
    "content_id": int(os.environ.get("SMOKE_CONTENT_ID", 2)),
    "run_id": int(os.environ.get("SMOKE_RUN_ID", 1)),
    "mention_id": int(os.environ.get("SMOKE_MENTION_ID", 6)),
}

# empty-but-valid is the expected state for these on most instances
EXPECTED_EMPTY_NOTE = {
    "get_keyword_history": "empty until rank scrapes run",
    "get_keyword_serp_features": "empty until rank scrapes run",
    "get_seo_metrics": "empty until rank scrapes run",
    "list_report_sheets": "empty without Google integrations",
    "get_report_sheet_data": "empty without Google integrations",
}


def build_args(schema: dict) -> dict | None:
    """Fill a tool's required params from DEFAULT_ARGS; None if impossible."""
    args = {}
    for name in schema.get("required", []):
        if name in DEFAULT_ARGS:
            args[name] = DEFAULT_ARGS[name]
        else:
            return None
    return args


def main() -> int:
    os.environ["PROMPTMAXX_MCP_ALLOW_INSIGHTS"] = "1"
    server = create_server()
    tools = asyncio.run(server.list_tools())
    failures = 0
    print(f"{'tool':<28} {'status':<8} {'ms':>6}  detail")
    print("-" * 84)

    for tool in sorted(tools, key=lambda t: t.name):
        schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", {}) or {}
        args = build_args(schema)
        if args is None:
            print(f"{tool.name:<28} {'SKIP':<8} {'':>6}  no default for a required param")
            continue
        start = time.monotonic()
        try:
            res = asyncio.run(server.call_tool(tool.name, args))
            ms = int((time.monotonic() - start) * 1000)
            text = res.content[0].text if res.content else ""
            if res.is_error:
                failures += 1
                print(f"{tool.name:<28} {'FAIL':<8} {ms:>6}  {text[:60]}")
                continue
            payload = json.loads(text)
            data = payload.get("data")
            size = len(data) if isinstance(data, (list, dict)) else 1
            note = EXPECTED_EMPTY_NOTE.get(tool.name, "")
            detail = f"{payload.get('source_endpoint', '?')} ({size} keys/rows)"
            if note and not size:
                detail += f" - ok, {note}"
            print(f"{tool.name:<28} {'PASS':<8} {ms:>6}  {detail}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            ms = int((time.monotonic() - start) * 1000)
            print(f"{tool.name:<28} {'FAIL':<8} {ms:>6}  {type(exc).__name__}: {exc}")

    print("-" * 84)
    print(f"{len(tools)} tools, {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
