"""httpx-based REST client with bearer-token injection.

Auth flow (OIDC PKCE loopback) and 401 refresh land in ``auth/`` in the next step; this
client takes a ``token_provider`` callable so it stays decoupled from how tokens are
obtained. Run all calls off the Qt UI thread.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

from zmetrics_desktop.config import Settings

# Returns the current access token, or None when unauthenticated.
TokenProvider = Callable[[], str | None]

# Attempts a token refresh; returns True if the request should be retried.
Refresher = Callable[[], bool]


class ApiError(RuntimeError):
    """Raised on a non-2xx response. Carries the status code and server detail."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"HTTP {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class ApiClient:
    def __init__(
        self,
        settings: Settings,
        token_provider: TokenProvider | None = None,
        refresher: Refresher | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._token_provider = token_provider or (lambda: None)
        self._refresher = refresher
        self._client = httpx.Client(
            base_url=settings.api_base,
            timeout=settings.request_timeout_s,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ApiClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _headers(self) -> dict[str, str]:
        token = self._token_provider()
        return {"Authorization": f"Bearer {token}"} if token else {}

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        resp = self._client.request(method, path, headers=self._headers(), **kwargs)
        if resp.status_code == 401 and self._refresher is not None and self._refresher():
            # Token refreshed — retry exactly once with the new bearer.
            resp = self._client.request(method, path, headers=self._headers(), **kwargs)
        if resp.is_success:
            if resp.status_code == 204 or not resp.content:
                return None
            return resp.json()
        detail = _extract_detail(resp)
        raise ApiError(resp.status_code, detail)

    def is_reachable(self) -> bool:
        """True when the backend ``/health`` endpoint answers (root path, no auth)."""
        url = f"{self._settings.backend_base_url.rstrip('/')}/health"
        try:
            return self._client.get(url).is_success
        except httpx.HTTPError:
            return False

    def get(self, path: str, params: dict | None = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, json: dict | None = None) -> Any:
        return self._request("POST", path, json=json)

    def post_multipart(self, path: str, data: dict, files: dict) -> Any:
        """POST a multipart form (file uploads). ``files``: httpx format, e.g.
        ``{"file": (filename, bytes, content_type)}``."""
        return self._request("POST", path, data=data, files=files)

    def patch(self, path: str, json: dict | None = None) -> Any:
        return self._request("PATCH", path, json=json)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)


def _extract_detail(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        if isinstance(body, dict) and "detail" in body:
            return str(body["detail"])
    except Exception:
        pass
    return resp.text or resp.reason_phrase
