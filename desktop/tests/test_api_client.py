import httpx
import pytest

from zmetrics_desktop.api.client import ApiClient, ApiError
from zmetrics_desktop.config import Settings


def _client(handler, token="tok", refresher=None) -> ApiClient:
    return ApiClient(
        Settings(),
        token_provider=lambda: token,
        refresher=refresher,
        transport=httpx.MockTransport(handler),
    )


def test_get_returns_json_and_sends_bearer():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("Authorization")
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"items": [], "total": 0})

    with _client(handler) as api:
        body = api.get("/quarries", params={"page": 1})

    assert body == {"items": [], "total": 0}
    assert seen["auth"] == "Bearer tok"
    assert seen["url"].startswith("http://localhost:8000/api/v1/quarries")


def test_error_raises_api_error_with_detail():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Quarry not found"})

    with _client(handler) as api, pytest.raises(ApiError) as exc:
        api.get("/quarries/123")
    assert exc.value.status_code == 404
    assert exc.value.detail == "Quarry not found"


def test_401_triggers_refresh_and_single_retry():
    calls = {"n": 0, "refreshed": 0}
    tokens = iter(["expired", "fresh", "fresh"])
    current = {"tok": "expired"}

    def refresher() -> bool:
        calls["refreshed"] += 1
        current["tok"] = "fresh"
        return True

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if request.headers["Authorization"] == "Bearer expired":
            return httpx.Response(401, json={"detail": "expired"})
        return httpx.Response(200, json={"ok": True})

    api = ApiClient(
        Settings(),
        token_provider=lambda: current["tok"],
        refresher=refresher,
        transport=httpx.MockTransport(handler),
    )
    assert api.get("/reports") == {"ok": True}
    assert calls["refreshed"] == 1
    assert calls["n"] == 2  # original + exactly one retry


def test_401_with_failed_refresh_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "expired"})

    api = _client(handler, refresher=lambda: False)
    with pytest.raises(ApiError) as exc:
        api.get("/reports")
    assert exc.value.status_code == 401


def test_204_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    with _client(handler) as api:
        assert api.delete("/admin/users/1") is None


def test_is_reachable_hits_root_health_without_auth_path():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"status": "ok"})

    with _client(handler) as api:
        assert api.is_reachable() is True
    # Root /health — not under /api/v1.
    assert seen["url"] == "http://localhost:8000/health"


def test_is_reachable_false_on_connect_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    with _client(handler) as api:
        assert api.is_reachable() is False


def test_is_reachable_false_on_5xx():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    with _client(handler) as api:
        assert api.is_reachable() is False
