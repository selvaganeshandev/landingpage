"""HTTP transport smoke test: auth gate + full MCP handshake through the door.

Usage:
    python scripts/smoke_http.py <api_key>          # server must be running with --http
"""

import asyncio
import sys

import httpx2 as httpx  # the SDK's bundled httpx fork
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

BASE = "http://127.0.0.1:8010/mcp"


async def main() -> int:
    key = sys.argv[1] if len(sys.argv) > 1 else ""
    failures = 0

    # 1. no key -> 401
    async with httpx.AsyncClient() as plain:
        r = await plain.post(BASE, json={})
        print(f"{'PASS' if r.status_code == 401 else 'FAIL'}  no-key request -> {r.status_code}")
        failures += r.status_code != 401

        r = await plain.post(BASE, json={}, headers={"Authorization": "Bearer not_a_service_key"})
        print(f"{'PASS' if r.status_code == 401 else 'FAIL'}  wrong-key request -> {r.status_code}")
        failures += r.status_code != 401

    # 2. valid key -> full MCP handshake, list tools, call a tool
    auth_client = httpx.AsyncClient(headers={"Authorization": f"Bearer {key}"})
    async with streamable_http_client(BASE, http_client=auth_client) as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            info = await session.initialize()
            print(f"PASS  initialize -> server '{info.server_info.name}'")
            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            ok = len(names) >= 26 and "list_clients" in names
            print(f"{'PASS' if ok else 'FAIL'}  tools/list -> {len(names)} tools")
            failures += not ok
            result = await session.call_tool("list_clients", {})
            text = result.content[0].text if result.content else ""
            ok = "Zerodha" in text or "total_count" in text
            print(f"{'PASS' if ok else 'FAIL'}  call list_clients -> {text[:60]}...")
            failures += not ok

    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
