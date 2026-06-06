"""Tests: GET /api/v1/analysis-results/{result_id} (GAP-1)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel
from tests.factories import build_chain, client_for, grant_access, jwt, make_user


@pytest.mark.asyncio
async def test_get_analysis_result_with_access(db_session: AsyncSession):
    owner = await make_user(db_session)
    chain = await build_chain(db_session, owner)
    await grant_access(db_session, owner.id, chain["quarry"].id, RoleLevel.USER)

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        resp = await ac.get(
            f"/api/v1/analysis-results/{chain['result'].id}",
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(chain["result"].id)
    assert data["p50_mm"] == pytest.approx(345.2, rel=1e-3)
    assert data["p80_mm"] == pytest.approx(580.8, rel=1e-3)
    assert data["total_particles_counted"] == 1847


@pytest.mark.asyncio
async def test_get_analysis_result_forbidden_without_access(db_session: AsyncSession):
    owner = await make_user(db_session)
    chain = await build_chain(db_session, owner)
    # A different caller with no QuarryUserAccess on this quarry.
    outsider_sub = f"outsider-{uuid.uuid4()}"

    async with client_for(db_session, jwt(outsider_sub)) as ac:
        resp = await ac.get(
            f"/api/v1/analysis-results/{chain['result'].id}",
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_analysis_result_not_found(db_session: AsyncSession):
    owner = await make_user(db_session)

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        resp = await ac.get(
            f"/api/v1/analysis-results/{uuid.uuid4()}",
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 404
