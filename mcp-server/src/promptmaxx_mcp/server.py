"""MCP server assembly and entry point."""

from __future__ import annotations

from mcp.server import MCPServer

from .client import PromptmaxxClient
from .config import Config, load_config
from .tools import backlinks as backlinks_tools
from .tools import clients as clients_tools
from .tools import competitors as competitors_tools
from .tools import content as content_tools
from .tools import keywords as keywords_tools
from .tools import reports as reports_tools
from .tools import seo as seo_tools
from .tools import visibility as visibility_tools


def create_server(config: Config | None = None) -> MCPServer:
    if config is None:
        config = load_config()
    client = PromptmaxxClient(config)
    mcp = MCPServer(
        "promptmaxx",
        instructions=(
            "Read-only access to Promptmaxx: AI-visibility mentions, share of "
            "voice, content gaps, SEO rank tracking, generated content, and "
            "site-health audits, per client. Call list_clients first to get a "
            "domain_id; every other tool requires one. This server never "
            "writes: it cannot trigger runs or spend the platform's model "
            "budget. Known data caveats are stated on the affected tools."
        ),
    )
    clients_tools.register(mcp, client)
    visibility_tools.register(mcp, client)
    competitors_tools.register(mcp, client, config)
    seo_tools.register(mcp, client)
    content_tools.register(mcp, client)
    keywords_tools.register(mcp, client)
    reports_tools.register(mcp, client)
    backlinks_tools.register(mcp, client)
    return mcp


class _ApiKeyPassthroughMiddleware:
    """Pure-ASGI middleware for the HTTP transport.

    Every request must carry a Promptmaxx service API key
    (Authorization: Bearer pmxk_... or Api-Key pmxk_..., minted in
    Settings > API keys). The key IS validated here, against the backend's
    GET /v1/me (cached in-process), so a bad key is a transport-level 401 —
    initialize never succeeds and no tool call reports a "successful"
    failure. Org scoping and the client-role read-only rule still apply
    server-side on every data call, which authenticates with this same key.

    Fail-open on backend outage: if /v1/me is unreachable the request goes
    through and the data call surfaces the real error — an API blip must
    not 401 every valid key.
    """

    # key -> (valid, monotonic expiry). Valid keys re-checked every 5 min
    # (revocation lag ceiling); invalid ones every 30s (a just-minted key).
    _TTL_OK = 300.0
    _TTL_BAD = 30.0

    def __init__(self, app, base_url: str):
        self.app = app
        self.base_url = base_url.rstrip("/")
        self._cache: dict[str, tuple[bool, float]] = {}

    async def _key_is_valid(self, token: str) -> bool:
        import time

        import httpx

        now = time.monotonic()
        hit = self._cache.get(token)
        if hit and hit[1] > now:
            return hit[0]
        try:
            async with httpx.AsyncClient(timeout=10.0) as http:
                resp = await http.get(
                    f"{self.base_url}/v1/me",
                    headers={"Authorization": f"Api-Key {token}"},
                )
        except httpx.HTTPError:
            return True  # fail open — see class docstring
        if resp.status_code == 429:
            return True  # rate-limited probe proves nothing about the key
        ok = resp.status_code == 200
        if len(self._cache) > 1024:
            self._cache = {k: v for k, v in self._cache.items() if v[1] > now}
        self._cache[token] = (ok, now + (self._TTL_OK if ok else self._TTL_BAD))
        return ok

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        auth = headers.get("authorization", "")
        token = ""
        lowered = auth.lower()
        if lowered.startswith("bearer "):
            token = auth[7:].strip()
        elif lowered.startswith("api-key "):
            token = auth[8:].strip()
        if not token.startswith("pmxk_"):
            import logging
            logging.getLogger(__name__).warning(
                "MCP HTTP auth denied (no service key) from %s", scope.get("client"))
            await send({
                "type": "http.response.start", "status": 401,
                "headers": [(b"content-type", b"application/json"),
                            (b"www-authenticate", b"Bearer")],
            })
            await send({"type": "http.response.body",
                        "body": b'{"error": "missing Promptmaxx service API key (pmxk_...)"}'})
            return
        if not await self._key_is_valid(token):
            import logging
            logging.getLogger(__name__).warning(
                "MCP HTTP auth denied (invalid service key) from %s", scope.get("client"))
            await send({
                "type": "http.response.start", "status": 401,
                "headers": [(b"content-type", b"application/json"),
                            (b"www-authenticate", b"Bearer")],
            })
            await send({"type": "http.response.body",
                        "body": b'{"error": "Promptmaxx service API key rejected (invalid, revoked, or expired)"}'})
            return
        from .client import current_api_key
        ctx_token = current_api_key.set(token)
        try:
            await self.app(scope, receive, send)
        finally:
            current_api_key.reset(ctx_token)


def _serve_http(mcp: MCPServer, host: str, port: int, base_url: str) -> None:
    import uvicorn

    app = mcp.streamable_http_app()
    uvicorn.run(_ApiKeyPassthroughMiddleware(app, base_url),
                host=host, port=port, log_level="info")


def main() -> None:
    import argparse
    import os

    parser = argparse.ArgumentParser(prog="promptmaxx-mcp")
    parser.add_argument("--http", action="store_true",
                        help="streamable-http transport on PROMPTMAXX_MCP_HTTP_HOST:PORT")
    args = parser.parse_args()

    use_http = args.http or os.environ.get("PROMPTMAXX_MCP_TRANSPORT", "").lower() == "http"

    # HTTP mode needs no server-side credentials: each request brings its own
    # Promptmaxx service API key and the backend is the authority.
    config = load_config(require_credentials=not use_http)
    mcp = create_server(config)
    if use_http:
        _serve_http(mcp, config.http_host, config.http_port, config.base_url)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
