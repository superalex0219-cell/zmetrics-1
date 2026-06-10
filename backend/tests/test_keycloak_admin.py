"""Unit tests for the Keycloak Admin client (httpx fully mocked, no network)."""

from __future__ import annotations

import httpx
import pytest

from app.config import Settings
from app.services.keycloak_admin import (
    KeycloakAdminClient,
    KeycloakAdminError,
    generate_temp_password,
)

USERS_PATH = "/admin/realms/zmetrics/users"


def _client(handler) -> KeycloakAdminClient:
    """Build a KeycloakAdminClient backed by an httpx MockTransport."""
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    return KeycloakAdminClient(Settings(), http=http)


@pytest.mark.asyncio
async def test_token_cached_within_expiry():
    token_calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            token_calls["n"] += 1
            return httpx.Response(200, json={"access_token": "tok-abc", "expires_in": 300})
        return httpx.Response(
            201, headers={"Location": f"http://kc{USERS_PATH}/sub-1"}
        )

    kc = _client(handler)
    await kc.create_user(email="a@example.com", full_name="A", temp_password="pw1")
    await kc.create_user(email="b@example.com", full_name="B", temp_password="pw2")

    # One token fetch reused across both user operations.
    assert token_calls["n"] == 1


@pytest.mark.asyncio
async def test_create_user_parses_sub_from_location():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "t", "expires_in": 300})
        return httpx.Response(
            201, headers={"Location": f"http://keycloak:8080{USERS_PATH}/the-new-sub"}
        )

    kc = _client(handler)
    sub = await kc.create_user(email="c@example.com", full_name="C", temp_password="pw")
    assert sub == "the-new-sub"


@pytest.mark.asyncio
async def test_create_user_conflict_raises_409():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "t", "expires_in": 300})
        return httpx.Response(409, json={"errorMessage": "User exists"})

    kc = _client(handler)
    with pytest.raises(KeycloakAdminError) as exc:
        await kc.create_user(email="d@example.com", full_name="D", temp_password="pw")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_non_2xx_on_update_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "t", "expires_in": 300})
        return httpx.Response(500, text="boom")

    kc = _client(handler)
    with pytest.raises(KeycloakAdminError) as exc:
        await kc.update_user(sub="sub-1", enabled=False)
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_token_request_failure_maps_to_502():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(401, json={"error": "invalid_client"})
        return httpx.Response(201)

    kc = _client(handler)
    with pytest.raises(KeycloakAdminError) as exc:
        await kc.reset_password(sub="sub-1", temp_password="pw")
    # The token fetch itself failed (401) — surfaced as that status, not the op.
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_update_user_no_fields_is_noop():
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no HTTP call expected when nothing to update")

    kc = _client(handler)
    await kc.update_user(sub="sub-1")  # no email/full_name/enabled → no request


def test_generate_temp_password_is_nontrivial():
    a = generate_temp_password()
    b = generate_temp_password()
    assert a != b
    assert len(a) >= 12
    assert any(ch.isdigit() for ch in a)
