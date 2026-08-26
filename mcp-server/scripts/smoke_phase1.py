"""Phase 1 smoke test: client auth path + the three M1 tools' endpoints.

Usage: set PROMPTMAXX_ACCESS_TOKEN (or PROMPTMAXX_EMAIL/PASSWORD), then
    python scripts/smoke_phase1.py
"""

import asyncio
import json
import sys

from promptmaxx_mcp.client import PromptmaxxClient, PromptmaxxError
from promptmaxx_mcp.config import load_config
from promptmaxx_mcp.server import create_server


def main() -> int:
    config = load_config()
    client = PromptmaxxClient(config)
    failures = 0

    def check(name, fn):
        nonlocal failures
        try:
            result = fn()
            data = result["data"]
            summary = f"list[{len(data)}]" if isinstance(data, list) else \
                f"dict keys={list(data)[:6]}" if isinstance(data, dict) else type(data).__name__
            print(f"PASS  {name:<18} {result['source_endpoint']:<38} {summary}")
        except PromptmaxxError as exc:
            failures += 1
            print(f"FAIL  {name:<18} {exc}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL  {name:<18} {type(exc).__name__}: {exc}")

    check("list_clients", lambda: client.get("/domains/"))
    check("get_client", lambda: client.get("/domains/1/"))
    check("get_site_health", lambda: client.get("/domains/1/health-check/", timeout=120.0))

    # tenancy/error mapping: a domain this credential cannot see must read clearly
    try:
        client.get("/domains/999999/")
        failures += 1
        print("FAIL  error_mapping      expected PromptmaxxError for unknown domain")
    except PromptmaxxError as exc:
        print(f"PASS  error_mapping      404 -> {str(exc)[:80]}")

    # server assembles and registers the expected tools
    server = create_server()
    tools = sorted(t.name for t in asyncio.run(server.list_tools()))
    expected = ["get_client", "get_site_health", "list_clients"]
    if tools == expected:
        print(f"PASS  tool_registry      {tools}")
    else:
        failures += 1
        print(f"FAIL  tool_registry      got {tools}, expected {expected}")

    client.close()
    print(json.dumps({"failures": failures}))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
