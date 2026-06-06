"""Tests: JWT decode, get_current_user, and require_quarry_role."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.quarry import Quarry
from app.db.models.user import QuarryUserAccess, Role, UserProfile


# ── helpers ───────────────────────────────────────────────────────────────────

def _jwt_payload(sub: str, email: str = "user@test.local", name: str = "Test User") -> dict:
    return {"sub": sub, "email": email, "name": name, "realm_access": {"roles": []}}


@asynccontextmanager
async def _http_client(db_session: AsyncSession, jwt_payload: dict):
    """AsyncClient with DB override and controlled JWT payload."""
    from app.db.session import get_db
    from app.main import app

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    try:
        with patch("app.dependencies.decode_token", new_callable=AsyncMock) as mock_decode:
            mock_decode.return_value = jwt_payload
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                yield ac
    finally:
        app.dependency_overrides.clear()


# ── Section A: JWT decode ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_decode_token_expired():
    from jose.exceptions import ExpiredSignatureError

    from app.auth.jwt import decode_token

    with patch("app.auth.jwt._fetch_jwks", new_callable=AsyncMock) as mock_jwks:
        mock_jwks.return_value = {}
        with patch("app.auth.jwt.jwt.decode") as mock_decode:
            mock_decode.side_effect = ExpiredSignatureError("expired")
            with pytest.raises(ValueError, match="expired"):
                await decode_token("fake.token")


@pytest.mark.asyncio
async def test_decode_token_invalid_signature():
    from jose import JWTError

    from app.auth.jwt import decode_token

    with patch("app.auth.jwt._fetch_jwks", new_callable=AsyncMock) as mock_jwks:
        mock_jwks.return_value = {}
        with patch("app.auth.jwt.jwt.decode") as mock_decode:
            mock_decode.side_effect = JWTError("bad signature")
            with pytest.raises(ValueError, match="Invalid token"):
                await decode_token("bad.token")


# ── Section B: get_current_user dependency ───────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_auto_provisions_new_user(db_session: AsyncSession):
    """First login: unknown sub → UserProfile created and returned."""
    from app.dependencies import get_current_user

    sub = f"new-sub-{uuid.uuid4()}"
    payload = _jwt_payload(sub, email=f"{sub}@test.local")

    with patch("app.dependencies.decode_token", new_callable=AsyncMock) as mock_decode:
        mock_decode.return_value = payload
        user = await get_current_user(token="fake", db=db_session)

    assert user.keycloak_sub == sub
    assert user.email == payload["email"]

    result = await db_session.execute(
        select(UserProfile).where(UserProfile.keycloak_sub == sub)
    )
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_get_current_user_returns_existing_user(db_session: AsyncSession):
    """Second login: known sub → same UserProfile returned without duplicate insert."""
    from app.dependencies import get_current_user

    sub = f"existing-{uuid.uuid4()}"
    existing = UserProfile(keycloak_sub=sub, email=f"{sub}@test.local", full_name="Existing")
    db_session.add(existing)
    await db_session.flush()

    with patch("app.dependencies.decode_token", new_callable=AsyncMock) as mock_decode:
        mock_decode.return_value = _jwt_payload(sub)
        user = await get_current_user(token="fake", db=db_session)

    assert user.id == existing.id


@pytest.mark.asyncio
async def test_get_current_user_disabled_user_raises_403(db_session: AsyncSession):
    """Disabled account → 403."""
    from app.dependencies import get_current_user

    sub = f"disabled-{uuid.uuid4()}"
    disabled = UserProfile(
        keycloak_sub=sub, email=f"{sub}@test.local", full_name="Disabled", is_active=False
    )
    db_session.add(disabled)
    await db_session.flush()

    with patch("app.dependencies.decode_token", new_callable=AsyncMock) as mock_decode:
        mock_decode.return_value = _jwt_payload(sub)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="fake", db=db_session)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_user_missing_sub_raises_401(db_session: AsyncSession):
    """Token without 'sub' claim → 401."""
    from app.dependencies import get_current_user

    with patch("app.dependencies.decode_token", new_callable=AsyncMock) as mock_decode:
        mock_decode.return_value = {"email": "x@test.local", "name": "X"}  # no sub
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="fake", db=db_session)

    assert exc_info.value.status_code == 401


# ── Section C: require_quarry_role via HTTP ───────────────────────────────────
# Uses POST /api/v1/quarries/{quarry_id}/sections (requires BLASTER = level 3).


@pytest_asyncio.fixture
async def quarry_for_role_tests(db_session: AsyncSession) -> Quarry:
    quarry = Quarry(name="Role-Test Quarry")
    db_session.add(quarry)
    await db_session.flush()
    return quarry


@pytest_asyncio.fixture
async def blaster_role(db_session: AsyncSession) -> Role:
    role = Role(name=f"blaster-{uuid.uuid4()}", level=3)
    db_session.add(role)
    await db_session.flush()
    return role


@pytest_asyncio.fixture
async def user_role(db_session: AsyncSession) -> Role:
    role = Role(name=f"user-{uuid.uuid4()}", level=1)
    db_session.add(role)
    await db_session.flush()
    return role


async def _post_section(ac: AsyncClient, quarry_id: uuid.UUID) -> int:
    resp = await ac.post(
        f"/api/v1/quarries/{quarry_id}/sections",
        json={"quarry_id": str(quarry_id), "name": "Test Block", "block_number": "T1"},
        headers={"Authorization": "Bearer fake"},
    )
    return resp.status_code


@pytest.mark.asyncio
async def test_require_quarry_role_no_access_returns_403(
    db_session: AsyncSession, quarry_for_role_tests: Quarry
):
    """User with no QuarryUserAccess row → 403."""
    sub = f"no-access-{uuid.uuid4()}"
    async with _http_client(db_session, _jwt_payload(sub)) as ac:
        code = await _post_section(ac, quarry_for_role_tests.id)
    assert code == 403


@pytest.mark.asyncio
async def test_require_quarry_role_revoked_access_returns_403(
    db_session: AsyncSession, quarry_for_role_tests: Quarry, blaster_role: Role
):
    """User with revoked_at set → 403."""
    sub = f"revoked-{uuid.uuid4()}"
    user = UserProfile(keycloak_sub=sub, email=f"{sub}@test.local", full_name="Revoked")
    db_session.add(user)
    await db_session.flush()

    access = QuarryUserAccess(
        user_id=user.id,
        quarry_id=quarry_for_role_tests.id,
        role_id=blaster_role.id,
        revoked_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(access)
    await db_session.flush()

    async with _http_client(db_session, _jwt_payload(sub)) as ac:
        code = await _post_section(ac, quarry_for_role_tests.id)
    assert code == 403


@pytest.mark.asyncio
async def test_require_quarry_role_insufficient_role_returns_403(
    db_session: AsyncSession, quarry_for_role_tests: Quarry, user_role: Role
):
    """User with level-1 (USER) role on BLASTER endpoint → 403."""
    sub = f"low-role-{uuid.uuid4()}"
    user = UserProfile(keycloak_sub=sub, email=f"{sub}@test.local", full_name="Low Role")
    db_session.add(user)
    await db_session.flush()

    access = QuarryUserAccess(
        user_id=user.id, quarry_id=quarry_for_role_tests.id, role_id=user_role.id
    )
    db_session.add(access)
    await db_session.flush()

    async with _http_client(db_session, _jwt_payload(sub)) as ac:
        code = await _post_section(ac, quarry_for_role_tests.id)
    assert code == 403


@pytest.mark.asyncio
async def test_require_quarry_role_sufficient_role_passes(
    db_session: AsyncSession, quarry_for_role_tests: Quarry, blaster_role: Role
):
    """User with level-3 (BLASTER) role on BLASTER endpoint → 201."""
    sub = f"blaster-{uuid.uuid4()}"
    user = UserProfile(keycloak_sub=sub, email=f"{sub}@test.local", full_name="Blaster")
    db_session.add(user)
    await db_session.flush()

    access = QuarryUserAccess(
        user_id=user.id, quarry_id=quarry_for_role_tests.id, role_id=blaster_role.id
    )
    db_session.add(access)
    await db_session.flush()

    async with _http_client(db_session, _jwt_payload(sub)) as ac:
        code = await _post_section(ac, quarry_for_role_tests.id)
    assert code == 201
