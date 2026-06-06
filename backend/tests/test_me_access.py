"""Tests: GET /api/v1/me/access."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel
from app.db.models.quarry import Quarry
from tests.factories import client_for, grant_access, jwt, make_user


@pytest.mark.asyncio
async def test_me_access_returns_roles(db_session: AsyncSession):
    user = await make_user(db_session)
    quarry = Quarry(name=f"Quarry {uuid.uuid4()}")
    db_session.add(quarry)
    await db_session.flush()
    await grant_access(db_session, user.id, quarry.id, RoleLevel.SURVEYOR)

    async with client_for(db_session, jwt(user.keycloak_sub)) as ac:
        resp = await ac.get("/api/v1/me/access", headers={"Authorization": "Bearer fake"})

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["quarry_id"] == str(quarry.id)
    assert data[0]["role_level"] == RoleLevel.SURVEYOR.value


@pytest.mark.asyncio
async def test_me_access_empty_for_no_access(db_session: AsyncSession):
    sub = f"noaccess-{uuid.uuid4()}"

    async with client_for(db_session, jwt(sub)) as ac:
        resp = await ac.get("/api/v1/me/access", headers={"Authorization": "Bearer fake"})

    assert resp.status_code == 200
    assert resp.json() == []
