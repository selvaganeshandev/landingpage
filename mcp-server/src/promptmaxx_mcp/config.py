"""Configuration from environment variables, with optional .env file.

The .env file is looked up next to the package root (mcp-server/.env),
then in the current working directory. Existing environment variables
always win over .env values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    base_url: str
    email: str | None
    password: str | None
    access_token: str | None
    allow_insights: bool
    api_key: str | None = None
    http_host: str = "127.0.0.1"
    http_port: int = 8010


def _load_dotenv() -> None:
    package_root = Path(__file__).resolve().parents[2]
    for candidate in (package_root / ".env", Path.cwd() / ".env"):
        if not candidate.is_file():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
        break


def load_config(require_credentials: bool = True) -> Config:
    _load_dotenv()
    base_url = os.environ.get("PROMPTMAXX_BASE_URL", "http://localhost:8000").rstrip("/")
    email = os.environ.get("PROMPTMAXX_EMAIL") or None
    password = os.environ.get("PROMPTMAXX_PASSWORD") or None
    access_token = os.environ.get("PROMPTMAXX_ACCESS_TOKEN") or None
    api_key = os.environ.get("PROMPTMAXX_API_KEY") or None
    allow_insights = os.environ.get("PROMPTMAXX_MCP_ALLOW_INSIGHTS", "0") == "1"

    if require_credentials and not api_key and not access_token and not (email and password):
        raise SystemExit(
            "Promptmaxx MCP: set PROMPTMAXX_EMAIL and PROMPTMAXX_PASSWORD "
            "(or PROMPTMAXX_ACCESS_TOKEN) in the environment or mcp-server/.env"
        )

    return Config(
        base_url=base_url,
        email=email,
        password=password,
        access_token=access_token,
        allow_insights=allow_insights,
        api_key=api_key,
        http_host=os.environ.get("PROMPTMAXX_MCP_HTTP_HOST", "127.0.0.1"),
        http_port=int(os.environ.get("PROMPTMAXX_MCP_HTTP_PORT", "8010")),
    )
