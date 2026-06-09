"""OIDC Authorization Code + PKCE via loopback redirect (RFC 8252).

Flow:
1. Bind a local HTTP server on ``http://127.0.0.1:<ephemeral port>/callback``
2. Open the system browser at the Keycloak authorize endpoint (S256 challenge + state)
3. Catch the ``code`` on the loopback, validate ``state``
4. Exchange the code for tokens at the token endpoint; store them in the OS keyring

The Keycloak client ``zmetrics-desktop`` is public — there is no client secret to embed.
``login()`` blocks until the browser round-trip completes; run it off the Qt UI thread.
Tokens are never logged.
"""
from __future__ import annotations

import threading
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from zmetrics_desktop.auth.pkce import generate_pkce_pair
from zmetrics_desktop.auth.token_store import Tokens, TokenStore
from zmetrics_desktop.config import Settings

CALLBACK_PATH = "/callback"
_SUCCESS_PAGE = (
    "<html><head><meta charset='utf-8'><title>ZMetrics</title></head>"
    "<body style='font-family:sans-serif;text-align:center;margin-top:20%'>"
    "<h2>Вход выполнен</h2><p>Можно закрыть это окно и вернуться в ZMetrics.</p>"
    "</body></html>"
)
_ERROR_PAGE = (
    "<html><head><meta charset='utf-8'><title>ZMetrics</title></head>"
    "<body style='font-family:sans-serif;text-align:center;margin-top:20%'>"
    "<h2>Ошибка входа</h2><p>Закройте окно и попробуйте снова в ZMetrics.</p>"
    "</body></html>"
)


class AuthError(RuntimeError):
    """Authentication failed (user denied, state mismatch, token exchange error)."""


@dataclass(frozen=True)
class OidcEndpoints:
    authorize_url: str
    token_url: str

    @classmethod
    def from_settings(cls, settings: Settings) -> OidcEndpoints:
        issuer = settings.oidc_issuer
        return cls(
            authorize_url=f"{issuer}/protocol/openid-connect/auth",
            token_url=f"{issuer}/protocol/openid-connect/token",
        )


@dataclass(frozen=True)
class CallbackResult:
    code: str | None
    state: str | None
    error: str | None


def parse_callback(path: str) -> CallbackResult:
    """Parse ``code``/``state``/``error`` from the loopback request path."""
    query = parse_qs(urlparse(path).query)

    def first(name: str) -> str | None:
        values = query.get(name)
        return values[0] if values else None

    return CallbackResult(code=first("code"), state=first("state"), error=first("error"))


def build_authorize_url(
    endpoints: OidcEndpoints,
    client_id: str,
    redirect_uri: str,
    challenge: str,
    state: str,
) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid profile email",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    return f"{endpoints.authorize_url}?{urlencode(params)}"


def _tokens_from_response(resp: httpx.Response) -> Tokens:
    if resp.status_code != 200:
        # Do not include the response body verbatim — it may echo sensitive values.
        raise AuthError(f"Token endpoint returned HTTP {resp.status_code}")
    body = resp.json()
    access = body.get("access_token")
    if not access:
        raise AuthError("Token endpoint response missing access_token")
    return Tokens(access_token=access, refresh_token=body.get("refresh_token"))


def exchange_code(
    endpoints: OidcEndpoints,
    client_id: str,
    code: str,
    verifier: str,
    redirect_uri: str,
    http: httpx.Client | None = None,
) -> Tokens:
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "code_verifier": verifier,
        "redirect_uri": redirect_uri,
    }
    client = http or httpx.Client(timeout=30.0)
    try:
        return _tokens_from_response(client.post(endpoints.token_url, data=data))
    finally:
        if http is None:
            client.close()


def refresh_tokens(
    endpoints: OidcEndpoints,
    client_id: str,
    refresh_token: str,
    http: httpx.Client | None = None,
) -> Tokens:
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }
    client = http or httpx.Client(timeout=30.0)
    try:
        return _tokens_from_response(client.post(endpoints.token_url, data=data))
    finally:
        if http is None:
            client.close()


class _LoopbackServer:
    """One-shot loopback HTTP server that captures a single OIDC callback."""

    def __init__(self) -> None:
        self.result: CallbackResult | None = None
        self._event = threading.Event()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 (http.server API)
                if urlparse(self.path).path != CALLBACK_PATH:
                    self.send_response(404)
                    self.end_headers()
                    return
                parsed = parse_callback(self.path)
                page = _SUCCESS_PAGE if parsed.code and not parsed.error else _ERROR_PAGE
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page.encode("utf-8"))
                outer.result = parsed
                outer._event.set()

            def log_message(self, *args: object) -> None:
                # Never log callback URLs — they contain the authorization code.
                pass

        # Port 0 = OS-assigned ephemeral port (Keycloak redirect allows localhost:*).
        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self._server.timeout = 1.0

    @property
    def redirect_uri(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}{CALLBACK_PATH}"

    def wait_for_callback(self, timeout_s: float) -> CallbackResult:
        thread = threading.Thread(target=self._serve_until_done, daemon=True)
        thread.start()
        try:
            if not self._event.wait(timeout=timeout_s):
                raise AuthError("Timed out waiting for the browser login")
            assert self.result is not None
            return self.result
        finally:
            # Stop the serving loop (also on timeout) and only then close the socket,
            # so the thread never calls handle_request() on a closed server.
            self._event.set()
            thread.join(timeout=2.0)
            self._server.server_close()

    def _serve_until_done(self) -> None:
        while not self._event.is_set():
            try:
                self._server.handle_request()
            except (OSError, ValueError):
                return  # socket closed during shutdown


class AuthManager:
    """High-level auth API: interactive login, token access, refresh, logout."""

    def __init__(
        self,
        settings: Settings,
        token_store: TokenStore | None = None,
        browser_opener=webbrowser.open,
    ) -> None:
        self._settings = settings
        self._endpoints = OidcEndpoints.from_settings(settings)
        self._store = token_store or TokenStore()
        self._open_browser = browser_opener

    def access_token(self) -> str | None:
        return self._store.access_token()

    def login(self, timeout_s: float = 180.0) -> Tokens:
        """Interactive PKCE login. Blocking — run off the UI thread."""
        import secrets

        pkce = generate_pkce_pair()
        state = secrets.token_urlsafe(24)
        server = _LoopbackServer()
        url = build_authorize_url(
            self._endpoints,
            self._settings.keycloak_client_id,
            server.redirect_uri,
            pkce.challenge,
            state,
        )
        self._open_browser(url)
        result = server.wait_for_callback(timeout_s)

        if result.error:
            raise AuthError(f"Authorization denied: {result.error}")
        if not result.code:
            raise AuthError("Callback did not contain an authorization code")
        if result.state != state:
            raise AuthError("State mismatch — possible CSRF, aborting login")

        tokens = exchange_code(
            self._endpoints,
            self._settings.keycloak_client_id,
            result.code,
            pkce.verifier,
            server.redirect_uri,
        )
        self._store.save(tokens)
        return tokens

    def refresh(self) -> bool:
        """Refresh the token pair. Returns True on success, False if re-login is needed."""
        current = self._store.load()
        if current is None or not current.refresh_token:
            return False
        try:
            tokens = refresh_tokens(
                self._endpoints,
                self._settings.keycloak_client_id,
                current.refresh_token,
            )
        except AuthError:
            return False
        self._store.save(tokens)
        return True

    def logout(self) -> None:
        self._store.clear()
