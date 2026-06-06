"""Tests: admin user management (PATCH/DELETE /api/v1/admin/users/{id})."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel
from app.db.models.quarry import Quarry
from app.db.models.user import UserProfile
from tests.factories import client_for, grant_access, jwt, make_user


async def _admin_user(db_session: AsyncSession) -> UserProfile:
    """A user that is ADMIN on at least one quarry (satisfies require_any_admin)."""
    admin = await make_user(db_session, full_name="Admin User")
    quarry = Quarry(name=f"Quarry {uuid.uuid4()}")
    db_session.add(quarry)
    await db_session.flush()
    await grant_access(db_session, admin.id, quarry.id, RoleLevel.ADMIN)
    return admin


@pytest.mark.asyncio
async def test_update_user_full_name(db_session: AsyncSession):
    admin = await _admin_user(db_session)
    target = await make_user(db_session, full_name="Old Name")

    async with client_for(db_session, jwt(admin.keycloak_sub)) as ac:
        resp = await ac.patch(
            f"/api/v1/admin/users/{target.id}",
            json={"full_name": "New Name"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    assert resp.json()["full_name"] == "New Name"


@pytest.mark.asyncio
async def test_deactivate_user_sets_inactive(db_session: AsyncSession):
    admin = await _admin_user(db_session)
    target = await make_user(db_session)

    async with client_for(db_session, jwt(admin.keycloak_sub)) as ac:
        resp = await ac.delete(
            f"/api/v1/admin/users/{target.id}",
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 204
    refreshed = (await db_session.execute(
        select(UserProfile).where(UserProfile.id == target.id)
    )).scalar_one()
    assert refreshed.is_active is False


@pytest.mark.asyncio
async def test_self_deactivation_blocked(db_session: AsyncSession):
    admin = await _admin_user(db_session)

    async with client_for(db_session, jwt(admin.keycloak_sub)) as ac:
        resp = await ac.delete(
            f"/api/v1/admin/users/{admin.id}",
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 400
