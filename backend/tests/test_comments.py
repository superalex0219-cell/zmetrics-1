"""Tests: POST /reports/{report_id}/recommendations/{rec_id}/comments (SEC-1 IDOR)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel
from tests.factories import build_chain, client_for, grant_access, jwt, make_user


@pytest.mark.asyncio
async def test_add_comment_success(db_session: AsyncSession):
    """Positive control: rec belongs to the report in the path -> 201."""
    owner = await make_user(db_session)
    chain = await build_chain(db_session, owner)
    await grant_access(db_session, owner.id, chain["quarry"].id, RoleLevel.USER)

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        resp = await ac.post(
            f"/api/v1/reports/{chain['report'].id}"
            f"/recommendations/{chain['recommendation'].id}/comments",
            json={"body": "Looks reasonable, reviewing."},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 201
    assert resp.json()["recommendation_id"] == str(chain["recommendation"].id)


@pytest.mark.asyncio
async def test_add_comment_wrong_report_rejected(db_session: AsyncSession):
    """SEC-1: a recommendation from a different report must not be commentable
    by pairing it with a report the caller can access -> 404."""
    owner = await make_user(db_session)
    chain_a = await build_chain(db_session, owner)
    chain_b = await build_chain(db_session, owner)
    # Caller has access to chain_a's quarry (passes the quarry RBAC gate)...
    await grant_access(db_session, owner.id, chain_a["quarry"].id, RoleLevel.USER)

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        resp = await ac.post(
            # ...but rec_id belongs to report B, not report A.
            f"/api/v1/reports/{chain_a['report'].id}"
            f"/recommendations/{chain_b['recommendation'].id}/comments",
            json={"body": "Trying to comment across reports."},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 404
