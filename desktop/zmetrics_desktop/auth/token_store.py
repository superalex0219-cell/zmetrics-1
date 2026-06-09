"""Secure token storage backed by the OS keyring.

On Windows this uses the Credential Manager. Tokens are never written to disk in
plaintext and never logged.
"""
from __future__ import annotations

from dataclasses import dataclass

import keyring

_SERVICE = "zmetrics-desktop"
_ACCESS = "access_token"
_REFRESH = "refresh_token"


@dataclass(frozen=True)
class Tokens:
    access_token: str
    refresh_token: str | None


class TokenStore:
    """Thin wrapper over ``keyring`` for the access/refresh token pair."""

    def __init__(self, service: str = _SERVICE) -> None:
        self._service = service

    def save(self, tokens: Tokens) -> None:
        keyring.set_password(self._service, _ACCESS, tokens.access_token)
        if tokens.refresh_token is not None:
            keyring.set_password(self._service, _REFRESH, tokens.refresh_token)

    def load(self) -> Tokens | None:
        access = keyring.get_password(self._service, _ACCESS)
        if not access:
            return None
        refresh = keyring.get_password(self._service, _REFRESH)
        return Tokens(access_token=access, refresh_token=refresh)

    def access_token(self) -> str | None:
        return keyring.get_password(self._service, _ACCESS)

    def clear(self) -> None:
        for key in (_ACCESS, _REFRESH):
            try:
                keyring.delete_password(self._service, key)
            except keyring.errors.PasswordDeleteError:
                pass
