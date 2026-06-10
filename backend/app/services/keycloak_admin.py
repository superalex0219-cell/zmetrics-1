"""Keycloak Admin REST API client (user management).

Thin async ``httpx`` wrapper used by the admin user-management endpoints to
create users, sync profile/email/enabled state, and reset passwords in Keycloak
so app accounts can actually authenticate.

Security notes:
- The client secret and bearer tokens are NEVER logged or returned.
- Authenticates via the ``zmetrics-backend`` service account (client_credentials).
- The caller (router) enforces ``require_any_admin`` and the feature flag; this
  module performs no authorization of its own.
"""

from __future__ import annotations

import asyncio
import secrets
import time

import httpx

from app.config import Settings, get_settings

# Refresh the cached service-account token this many seconds before it expires,
# so an in-flight request never races a server-side expiry.
_TOKEN_REFRESH_SKEW_S = 30
_HTTP_TIMEOUT_S = 10.0


class KeycloakAdminError(Exception):
    """Raised on a non-2xx response (or transport failure) from Keycloak.

    Carries an HTTP-ish ``status_code`` so the router can map it to a client
    response without echoing raw Keycloak internals.
    """

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"Keycloak admin error {status_code}: {message}")


def generate_temp_password() -> str:
    """Generate a one-time temporary password.

    ``token_urlsafe`` mixes upper/lower/digits; we append an explicit digit to
    guarantee a numeric character against a Keycloak password policy. The value
    is returned to the admin once and never persisted or logged.
    """
    return secrets.token_urlsafe(12) + str(secrets.randbelow(10))


class KeycloakAdminClient:
    """Async client for the subset of the Keycloak Admin API we need."""

    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._http = http
        self._owns_http = http is None
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._token_lock = asyncio.Lock()

    # ── HTTP plumbing ────────────────────────────────────────────────────────
    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=_HTTP_TIMEOUT_S)
        return self._http

    async def aclose(self) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()
            self._http = None

    # ── Auth ─────────────────────────────────────────────────────────────────
    async def _admin_token(self) -> str:
        """Return a valid service-account access token, refreshing on demand.

        Cached in-memory until ~30s before expiry. Never logged.
        """
        if self._token is not None and time.monotonic() < self._token_expires_at:
            return self._token

        async with self._token_lock:
            # Re-check inside the lock — another coroutine may have refreshed.
            if self._token is not None and time.monotonic() < self._token_expires_at:
                return self._token
            try:
                resp = await self._client().post(
                    self._settings.kc_token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._settings.kc_client_id,
                        "client_secret": self._settings.kc_client_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            except httpx.HTTPError as exc:
                raise KeycloakAdminError(502, f"Keycloak token request failed: {type(exc).__name__}")

            if resp.status_code != 200:
                # Do not surface the body — it can echo client credentials context.
                raise KeycloakAdminError(resp.status_code, "Failed to obtain admin token")

            payload = resp.json()
            self._token = payload["access_token"]
            expires_in = int(payload.get("expires_in", 60))
            self._token_expires_at = time.monotonic() + max(expires_in - _TOKEN_REFRESH_SKEW_S, 0)
            return self._token

    async def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {await self._admin_token()}"}

    async def _request(self, method: str, url: str, *, json: dict | None = None) -> httpx.Response:
        try:
            return await self._client().request(
                method, url, json=json, headers=await self._auth_headers()
            )
        except httpx.HTTPError as exc:
            raise KeycloakAdminError(502, f"Keycloak request failed: {type(exc).__name__}")

    # ── User operations ──────────────────────────────────────────────────────
    async def create_user(self, *, email: str, full_name: str, temp_password: str) -> str:
        """Create a user and return the new Keycloak subject id (``sub``).

        Raises ``KeycloakAdminError(409)`` if the username/email already exists.
        """
        resp = await self._request(
            "POST",
            self._settings.kc_admin_users_url,
            json={
                "username": email,
                "email": email,
                "firstName": full_name,
                "enabled": True,
                "emailVerified": False,
                "credentials": [
                    {"type": "password", "value": temp_password, "temporary": True}
                ],
            },
        )
        if resp.status_code == 201:
            location = resp.headers.get("Location", "")
            sub = location.rstrip("/").rsplit("/", 1)[-1]
            if not sub:
                raise KeycloakAdminError(502, "Keycloak did not return a user id")
            return sub
        if resp.status_code == 409:
            raise KeycloakAdminError(409, "user exists")
        raise KeycloakAdminError(resp.status_code, "Failed to create user")

    async def update_user(
        self,
        *,
        sub: str,
        email: str | None = None,
        full_name: str | None = None,
        enabled: bool | None = None,
    ) -> None:
        """Patch the given fields on a Keycloak user (only the ones provided)."""
        body: dict = {}
        if email is not None:
            body["email"] = email
        if full_name is not None:
            body["firstName"] = full_name
        if enabled is not None:
            body["enabled"] = enabled
        if not body:
            return  # nothing to sync

        resp = await self._request(
            "PUT", f"{self._settings.kc_admin_users_url}/{sub}", json=body
        )
        if resp.status_code not in (200, 204):
            raise KeycloakAdminError(resp.status_code, "Failed to update user")

    async def reset_password(self, *, sub: str, temp_password: str) -> None:
        """Set a one-time temporary password for the given Keycloak user."""
        resp = await self._request(
            "PUT",
            f"{self._settings.kc_admin_users_url}/{sub}/reset-password",
            json={"type": "password", "value": temp_password, "temporary": True},
        )
        if resp.status_code not in (200, 204):
            raise KeycloakAdminError(resp.status_code, "Failed to reset password")


# Module-level singleton so the in-memory token cache survives across requests.
_client_singleton: KeycloakAdminClient | None = None


def get_keycloak_admin_client() -> KeycloakAdminClient:
    """FastAPI dependency returning the shared admin client.

    Constructing it makes no network calls (the token is fetched lazily on the
    first user operation), so it is safe to inject even when the feature flag is
    off. Tests override this dependency with a fake.
    """
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = KeycloakAdminClient(get_settings())
    return _client_singleton
