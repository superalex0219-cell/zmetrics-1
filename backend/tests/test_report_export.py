"""Tests: GET /api/v1/reports/{report_id}/export (BLASTER+ only)."""

from __future__ import annotations

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel
from tests.factories import build_chain, client_for, grant_access, jwt, make_user


@pytest.mark.asyncio
async def test_export_returns_json_for_blaster(db_session: AsyncSession):
    owner = await make_user(db_session)
    chain = await build_chain(db_session, owner)
    await grant_access(db_session, owner.id, chain["quarry"].id, RoleLevel.BLASTER)

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        resp = await ac.get(
            f"/api/v1/reports/{chain['report'].id}/export",
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    assert "attachment" in resp.headers["content-disposition"]
    payload = json.loads(resp.content)
    assert payload["report"]["id"] == str(chain["report"].id)
    assert payload["analysis_result"]["p50_mm"] == pytest.approx(345.2, rel=1e-3)


@pytest.mark.asyncio
async def test_export_forbidden_for_user_role(db_session: AsyncSession):
    owner = await make_user(db_session)
    chain = await build_chain(db_session, owner)
    await grant_access(db_session, owner.id, chain["quarry"].id, RoleLevel.USER)

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        resp = await ac.get(
            f"/api/v1/reports/{chain['report'].id}/export",
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 403
