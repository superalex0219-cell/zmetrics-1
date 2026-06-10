"""Authentication against the public Keycloak client ``zmetrics-desktop``.

Primary flow (product decision 2026-06-11): in-app login form → direct access
grant (``AuthManager.login_password``) — браузер не открывается; пароль уходит
только на token endpoint Keycloak и нигде не сохраняется. The PKCE-loopback
browser flow (``AuthManager.login``) is kept as an alternative for environments
where ROPC is disabled. Tokens live in the OS keyring (Windows Credential
Manager) — never plaintext, never logged.
"""
from zmetrics_desktop.auth.oidc import AuthError, AuthManager
from zmetrics_desktop.auth.token_store import Tokens, TokenStore

__all__ = ["AuthError", "AuthManager", "Tokens", "TokenStore"]
