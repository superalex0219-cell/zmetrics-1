"""Authentication: OIDC Authorization Code + PKCE via loopback redirect.

Interactive login opens the system browser against the public Keycloak client
``zmetrics-desktop`` (no embedded secret) and catches the redirect on a loopback HTTP
server. Tokens live in the OS keyring (Windows Credential Manager) — never plaintext,
never logged.
"""
from zmetrics_desktop.auth.oidc import AuthError, AuthManager
from zmetrics_desktop.auth.token_store import Tokens, TokenStore

__all__ = ["AuthError", "AuthManager", "Tokens", "TokenStore"]
