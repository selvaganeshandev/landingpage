"""HTTP client for the Promptmaxx API.

The only module that talks HTTP. Handles login (POST /auth/login/),
in-memory token caching, one re-login on 401, and one retry with backoff
on transient failures (429/502/503/504 and connect errors).

Re-login on expiry instead of using the refresh token: refresh tokens
rotate on this backend, so a second process sharing the account would
invalidate ours. A fresh login has no such race for a single process.
"""

from __future__ import annotations

import time
from contextvars import ContextVar
from typing import Any

import httpx

from .config import Config
from .errors import readable_500

# Per-request Promptmaxx service API key (HTTP transport passthrough):
# the middleware stores the caller's key here; every backend call in that
# request then authenticates as the key's organisation. Stdio mode leaves
# it unset and falls back to config credentials.
current_api_key: ContextVar[str | None] = ContextVar("current_api_key", default=None)

_TRANSIENT_STATUSES = {429, 502, 503, 504}
_RETRY_DELAY_SECONDS = 2.0


class PromptmaxxError(RuntimeError):
    """Readable API failure, safe to surface as a tool error."""


class PromptmaxxClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._http = httpx.Client(base_url=config.base_url, timeout=30.0)
        self._token: str | None = config.access_token

    def close(self) -> None:
        self._http.close()

    # -- auth ---------------------------------------------------------------

    def _login(self) -> None:
        if not (self._config.email and self._config.password):
            raise PromptmaxxError(
                "Access token rejected (401) and no PROMPTMAXX_EMAIL/"
                "PROMPTMAXX_PASSWORD configured to log in with."
            )
        try:
            response = self._http.post(
                "/auth/login/",
                json={"email": self._config.email, "password": self._config.password},
            )
        except httpx.HTTPError as exc:
            raise PromptmaxxError(f"Cannot reach Promptmaxx at {self._config.base_url}: {exc}") from exc
        if response.status_code != 200:
            raise PromptmaxxError(
                f"Login failed ({response.status_code}): {response.text[:300]}"
            )
        token = response.json().get("access")
        if not isinstance(token, str):
            raise PromptmaxxError(
                f"Login succeeded but response had no 'access' token; keys: {list(response.json())}"
            )
        self._token = token

    # -- requests -----------------------------------------------------------

    def get(self, path: str, params: dict[str, Any] | None = None,
            timeout: float | None = None) -> dict[str, Any]:
        """GET a JSON endpoint. Returns {"source_endpoint": path, "data": ...}.

        Every response names its endpoint so callers can say which surface a
        number came from (the API reports the same metric differently on
        different endpoints — finding F4).
        """
        response = self._request(path, params, timeout)

        if response.status_code == 401:
            if current_api_key.get() or self._config.api_key:
                raise PromptmaxxError(
                    "API key rejected by Promptmaxx (invalid, revoked, or expired)."
                )
            self._token = None
            self._login()
            response = self._request(path, params, timeout)

        if response.status_code in _TRANSIENT_STATUSES:
            time.sleep(_RETRY_DELAY_SECONDS)
            response = self._request(path, params, timeout)

        self._raise_readable(response, path)

        try:
            data = response.json()
        except ValueError as exc:
            raise PromptmaxxError(
                f"{path} returned non-JSON (status {response.status_code}): "
                f"{response.text[:200]}"
            ) from exc
        return {"source_endpoint": path, "data": data}

    def _auth_header(self) -> dict[str, str]:
        request_key = current_api_key.get()
        if request_key:
            return {"Authorization": f"Api-Key {request_key}"}
        if self._config.api_key:
            return {"Authorization": f"Api-Key {self._config.api_key}"}
        if self._token is None:
            self._login()
        return {"Authorization": f"Bearer {self._token}"}

    def _request(self, path: str, params: dict[str, Any] | None,
                 timeout: float | None) -> httpx.Response:
        try:
            return self._http.get(
                path,
                params=params,
                headers=self._auth_header(),
                timeout=timeout if timeout is not None else httpx.USE_CLIENT_DEFAULT,
            )
        except httpx.HTTPError as exc:
            raise PromptmaxxError(f"Request to {path} failed: {exc}") from exc

    @staticmethod
    def _raise_readable(response: httpx.Response, path: str) -> None:
        if response.status_code < 400:
            return
        if response.status_code == 401:
            raise PromptmaxxError("Still unauthorized after re-login; check credentials.")
        if response.status_code == 403:
            raise PromptmaxxError(f"{path}: forbidden — this credential lacks access.")
        if response.status_code == 404:
            raise PromptmaxxError(
                f"{path}: not found. Either the id is wrong or the domain is not "
                "scoped to this credential (the tenancy check returns 404, not 403)."
            )
        known = readable_500(path, response.text)
        if known:
            raise PromptmaxxError(known)
        raise PromptmaxxError(
            f"{path} failed ({response.status_code}): {response.text[:300]}"
        )
