"""Keycloak JWT validation with JWKS fetching and caching."""

import asyncio
import time
from typing import Any

import httpx
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from app.config import get_settings

settings = get_settings()

_jwks_cache: dict[str, Any] = {}
_jwks_lock = asyncio.Lock()
_jwks_fetched_at: float = 0.0
_JWKS_TTL_SECONDS = 300  # re-fetch JWKS every 5 minutes


async def _fetch_jwks() -> dict:
    global _jwks_cache, _jwks_fetched_at
    async with _jwks_lock:
        now = time.monotonic()
        if _jwks_cache and (now - _jwks_fetched_at) < _JWKS_TTL_SECONDS:
            return _jwks_cache

        retries = 5
        delay = 2.0
        last_exc: Exception | None = None
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(settings.jwks_url)
                    resp.raise_for_status()
                    _jwks_cache = resp.json()
                    _jwks_fetched_at = time.monotonic()
                    return _jwks_cache
            except Exception as exc:
                last_exc = exc
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 30.0)

        raise RuntimeError(f"Failed to fetch JWKS from {settings.jwks_url}") from last_exc


async def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a Keycloak JWT. Returns the claims payload."""
    try:
        jwks = await _fetch_jwks()
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload
    except ExpiredSignatureError:
        raise ValueError("Token has expired")
    except JWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc


def extract_roles(payload: dict) -> list[str]:
    """Extract Keycloak realm roles from JWT payload."""
    return payload.get("realm_access", {}).get("roles", [])
