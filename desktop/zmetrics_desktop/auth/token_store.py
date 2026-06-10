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
_ACCESS_EXP = "access_expires_at"
_REFRESH_EXP = "refresh_expires_at"


@dataclass(frozen=True)
class Tokens:
    access_token: str
    refresh_token: str | None
    # Unix-эпоха (секунды); None, когда сервер не сообщил expires_in.
    access_expires_at: float | None = None
    refresh_expires_at: float | None = None


def _to_float(value: str | None) -> float | None:
    try:
        return float(value) if value else None
    except ValueError:
        return None


class TokenStore:
    """Thin wrapper over ``keyring`` for the access/refresh token pair."""

    def __init__(self, service: str = _SERVICE) -> None:
        self._service = service

    def save(self, tokens: Tokens) -> None:
        keyring.set_password(self._service, _ACCESS, tokens.access_token)
        if tokens.refresh_token is not None:
            keyring.set_password(self._service, _REFRESH, tokens.refresh_token)
        for key, value in ((_ACCESS_EXP, tokens.access_expires_at),
                           (_REFRESH_EXP, tokens.refresh_expires_at)):
            if value is not None:
                keyring.set_password(self._service, key, repr(float(value)))

    def load(self) -> Tokens | None:
        access = keyring.get_password(self._service, _ACCESS)
        if not access:
            return None
        return Tokens(
            access_token=access,
            refresh_token=keyring.get_password(self._service, _REFRESH),
            access_expires_at=_to_float(keyring.get_password(self._service, _ACCESS_EXP)),
            refresh_expires_at=_to_float(keyring.get_password(self._service, _REFRESH_EXP)),
        )

    def access_token(self) -> str | None:
        return keyring.get_password(self._service, _ACCESS)

    def clear(self) -> None:
        for key in (_ACCESS, _REFRESH, _ACCESS_EXP, _REFRESH_EXP):
            try:
                keyring.delete_password(self._service, key)
            except keyring.errors.PasswordDeleteError:
                pass
