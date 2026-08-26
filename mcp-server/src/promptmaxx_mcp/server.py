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
    Settings > API keys). The key is NOT validated here — it is stored in a
    request-scoped contextvar and every backend call of the request
    authenticates with it, so Promptmaxx itself is the authority: an
    invalid/revoked key fails there with 401, org scoping and the
    client-role read-only rule apply server-side.
    """

    def __init__(self, app):
        self.app = app

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
        from .client import current_api_key
        ctx_token = current_api_key.set(token)
        try:
            await self.app(scope, receive, send)
        finally:
            current_api_key.reset(ctx_token)


def _serve_http(mcp: MCPServer, host: str, port: int) -> None:
    import uvicorn

    app = mcp.streamable_http_app()
    uvicorn.run(_ApiKeyPassthroughMiddleware(app), host=host, port=port, log_level="info")


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
        _serve_http(mcp, config.http_host, config.http_port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
