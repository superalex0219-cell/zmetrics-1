from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.quarry import Quarry
from app.db.models.user import QuarryUserAccess, Role, UserProfile
from tests.factories import client_for, grant_access, jwt, make_user


@pytest.mark.asyncio
async def test_create_first_quarry_bootstraps_admin_access(db_session: AsyncSession):
    sub = f"bootstrap-{uuid.uuid4()}"

    async with client_for(db_session, jwt(sub)) as ac:
        response = await ac.post(
            "/api/v1/quarries",
            json={"name": "Startup Quarry", "location_description": "first site"},
            headers={"Authorization": "Bearer fake"},
        )

        assert response.status_code == 201
        quarry_id = response.json()["id"]

        listed = await ac.get("/api/v1/quarries", headers={"Authorization": "Bearer fake"})
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()["items"]] == [quarry_id]

        section = await ac.post(
            f"/api/v1/quarries/{quarry_id}/sections",
            json={"name": "Block A", "block_number": "A-1"},
            headers={"Authorization": "Bearer fake"},
        )
        assert section.status_code == 201

    user = (
        await db_session.execute(select(UserProfile).where(UserProfile.keycloak_sub == sub))
    ).scalar_one()
    access = (
        await db_session.execute(
            select(QuarryUserAccess)
            .join(Role, Role.id == QuarryUserAccess.role_id)
            .where(
                QuarryUserAccess.user_id == user.id,
                QuarryUserAccess.quarry_id == uuid.UUID(quarry_id),
                QuarryUserAccess.revoked_at.is_(None),
                Role.name == "admin",
                Role.level == 4,
            )
        )
    ).scalar_one_or_none()
    assert access is not None


@pytest.mark.asyncio
async def test_create_quarry_requires_admin_after_bootstrap(db_session: AsyncSession):
    quarry = Quarry(name="Existing Quarry")
    db_session.add(quarry)
    await db_session.flush()

    async with client_for(db_session, jwt(f"outsider-{uuid.uuid4()}")) as ac:
        response = await ac.post(
            "/api/v1/quarries",
            json={"name": "Forbidden Quarry"},
            headers={"Authorization": "Bearer fake"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_creator_gets_access_to_new_quarry(db_session: AsyncSession):
    admin = await make_user(db_session, "admin-user")
    existing = Quarry(name="Existing Quarry")
    db_session.add(existing)
    await db_session.flush()
    await grant_access(db_session, admin.id, existing.id, 4)

    async with client_for(db_session, jwt(admin.keycloak_sub)) as ac:
        response = await ac.post(
            "/api/v1/quarries",
            json={"name": "Second Quarry"},
            headers={"Authorization": "Bearer fake"},
        )

    assert response.status_code == 201
    quarry_id = uuid.UUID(response.json()["id"])
    access = (
        await db_session.execute(
            select(QuarryUserAccess).where(
                QuarryUserAccess.user_id == admin.id,
                QuarryUserAccess.quarry_id == quarry_id,
                QuarryUserAccess.revoked_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    assert access is not None


@pytest.mark.asyncio
async def test_admin_with_multiple_accesses_can_create_quarry(db_session: AsyncSession):
    admin = await make_user(db_session, "multi-admin")
    first = Quarry(name="First Admin Quarry")
    second = Quarry(name="Second Admin Quarry")
    db_session.add_all([first, second])
    await db_session.flush()
    await grant_access(db_session, admin.id, first.id, 4)
    await grant_access(db_session, admin.id, second.id, 4)

    async with client_for(db_session, jwt(admin.keycloak_sub)) as ac:
        response = await ac.post(
            "/api/v1/quarries",
            json={"name": "Third Quarry"},
            headers={"Authorization": "Bearer fake"},
        )

    assert response.status_code == 201
