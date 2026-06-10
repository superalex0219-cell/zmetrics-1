import base64
import hashlib

import httpx
import pytest

from zmetrics_desktop.auth.oidc import (
    AuthError,
    AuthManager,
    OidcEndpoints,
    build_authorize_url,
    exchange_code,
    parse_callback,
    refresh_tokens,
)
from zmetrics_desktop.auth.pkce import generate_pkce_pair
from zmetrics_desktop.auth.token_store import Tokens
from zmetrics_desktop.config import Settings


class InMemoryTokenStore:
    """Test double — keeps tokens in memory instead of the OS keyring."""

    def __init__(self) -> None:
        self._tokens: Tokens | None = None

    def save(self, tokens: Tokens) -> None:
        self._tokens = tokens

    def load(self) -> Tokens | None:
        return self._tokens

    def access_token(self) -> str | None:
        return self._tokens.access_token if self._tokens else None

    def clear(self) -> None:
        self._tokens = None


def _endpoints() -> OidcEndpoints:
    return OidcEndpoints.from_settings(Settings())


# --- PKCE ---------------------------------------------------------------------------


def test_pkce_challenge_is_s256_of_verifier():
    pair = generate_pkce_pair()
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(pair.verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    assert pair.challenge == expected
    assert 43 <= len(pair.verifier) <= 128
    assert pair.method == "S256"


def test_pkce_pairs_are_unique():
    assert generate_pkce_pair().verifier != generate_pkce_pair().verifier


# --- URL building / callback parsing --------------------------------------------------


def test_authorize_url_contains_required_params():
    url = build_authorize_url(
        _endpoints(), "zmetrics-desktop", "http://127.0.0.1:5555/callback", "chal", "st"
    )
    assert url.startswith("http://localhost:8080/realms/zmetrics/protocol/openid-connect/auth?")
    for fragment in (
        "client_id=zmetrics-desktop",
        "response_type=code",
        "code_challenge=chal",
        "code_challenge_method=S256",
        "state=st",
    ):
        assert fragment in url


def test_parse_callback_extracts_code_and_state():
    result = parse_callback("/callback?code=abc&state=xyz")
    assert result.code == "abc"
    assert result.state == "xyz"
    assert result.error is None


def test_parse_callback_extracts_error():
    result = parse_callback("/callback?error=access_denied&state=xyz")
    assert result.code is None
    assert result.error == "access_denied"


# --- Token endpoint calls (MockTransport, no network) ---------------------------------


def _mock_token_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_exchange_code_returns_tokens():
    def handler(request: httpx.Request) -> httpx.Response:
        body = dict(pair.split("=") for pair in request.content.decode().split("&"))
        assert body["grant_type"] == "authorization_code"
        assert body["code"] == "the-code"
        assert body["code_verifier"] == "the-verifier"
        return httpx.Response(200, json={"access_token": "at", "refresh_token": "rt"})

    tokens = exchange_code(
        _endpoints(),
        "zmetrics-desktop",
        "the-code",
        "the-verifier",
        "http://127.0.0.1:5555/callback",
        http=_mock_token_client(handler),
    )
    assert tokens.access_token == "at"
    assert tokens.refresh_token == "rt"


def test_exchange_code_error_does_not_leak_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant", "secret": "leak"})

    with pytest.raises(AuthError) as exc:
        exchange_code(
            _endpoints(), "c", "code", "ver", "http://127.0.0.1:1/callback",
            http=_mock_token_client(handler),
        )
    assert "leak" not in str(exc.value)
    assert "400" in str(exc.value)


def test_refresh_tokens_success():
    def handler(request: httpx.Request) -> httpx.Response:
        body = dict(pair.split("=") for pair in request.content.decode().split("&"))
        assert body["grant_type"] == "refresh_token"
        return httpx.Response(200, json={"access_token": "new-at", "refresh_token": "new-rt"})

    tokens = refresh_tokens(
        _endpoints(), "zmetrics-desktop", "old-rt", http=_mock_token_client(handler)
    )
    assert tokens.access_token == "new-at"


# --- AuthManager ----------------------------------------------------------------------


def test_auth_manager_refresh_without_tokens_returns_false():
    mgr = AuthManager(Settings(), token_store=InMemoryTokenStore())
    assert mgr.refresh() is False


def test_auth_manager_refresh_success(monkeypatch):
    store = InMemoryTokenStore()
    store.save(Tokens(access_token="old", refresh_token="rt"))
    mgr = AuthManager(Settings(), token_store=store)

    monkeypatch.setattr(
        "zmetrics_desktop.auth.oidc.refresh_tokens",
        lambda *a, **kw: Tokens(access_token="new", refresh_token="rt2"),
    )
    assert mgr.refresh() is True
    assert store.access_token() == "new"


def test_auth_manager_refresh_failure_returns_false(monkeypatch):
    store = InMemoryTokenStore()
    store.save(Tokens(access_token="old", refresh_token="rt"))
    mgr = AuthManager(Settings(), token_store=store)

    def boom(*a, **kw):
        raise AuthError("HTTP 400")

    monkeypatch.setattr("zmetrics_desktop.auth.oidc.refresh_tokens", boom)
    assert mgr.refresh() is False


def test_auth_manager_logout_clears_store():
    store = InMemoryTokenStore()
    store.save(Tokens(access_token="a", refresh_token="r"))
    AuthManager(Settings(), token_store=store).logout()
    assert store.access_token() is None


# --- Loopback server (real local HTTP round-trip) --------------------------------------


def test_loopback_server_captures_callback():
    import threading
    import urllib.request

    from zmetrics_desktop.auth.oidc import _LoopbackServer

    server = _LoopbackServer()
    uri = server.redirect_uri
    assert uri.startswith("http://127.0.0.1:")
    assert uri.endswith("/callback")

    def hit() -> None:
        with urllib.request.urlopen(f"{uri}?code=c0de&state=s7ate", timeout=5) as resp:
            assert resp.status == 200

    threading.Timer(0.2, hit).start()
    result = server.wait_for_callback(timeout_s=10)
    assert result.code == "c0de"
    assert result.state == "s7ate"
    assert result.error is None


def test_loopback_server_times_out():
    from zmetrics_desktop.auth.oidc import _LoopbackServer

    server = _LoopbackServer()
    with pytest.raises(AuthError, match="Timed out"):
        server.wait_for_callback(timeout_s=0.3)


# --- Password grant (форма логина в приложении, без браузера) -------------------------


def _password_http(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_password_grant_returns_tokens():
    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        assert "grant_type=password" in body
        assert "username=admin-user" in body
        assert "client_id=zmetrics-desktop" in body
        return httpx.Response(200, json={"access_token": "at-1", "refresh_token": "rt-1"})

    from zmetrics_desktop.auth.oidc import password_grant

    tokens = password_grant(
        _endpoints(), "zmetrics-desktop", "admin-user", "changeme",
        http=_password_http(handler),
    )
    assert tokens.access_token == "at-1"
    assert tokens.refresh_token == "rt-1"


def test_password_grant_invalid_credentials_friendly_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_grant"})

    from zmetrics_desktop.auth.oidc import password_grant

    with pytest.raises(AuthError, match="Неверный логин или пароль"):
        password_grant(
            _endpoints(), "zmetrics-desktop", "admin-user", "wrong",
            http=_password_http(handler),
        )


def test_login_password_stores_tokens(monkeypatch):
    store = InMemoryTokenStore()
    manager = AuthManager(Settings(), token_store=store)

    def fake_grant(endpoints, client_id, username, password, http=None):
        assert username == "admin-user"
        return Tokens(access_token="at-2", refresh_token="rt-2")

    monkeypatch.setattr("zmetrics_desktop.auth.oidc.password_grant", fake_grant)
    manager.login_password("admin-user", "changeme")
    assert store.access_token() == "at-2"
