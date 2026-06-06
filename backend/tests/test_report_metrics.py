"""Tests: ReportRead.analysis_method safety label (GAP-2).

analysis_method MUST be derived from ModelVersion.model_type, never hardcoded.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel
from tests.factories import build_chain, client_for, grant_access, jwt, make_user


async def _get_report(db_session, *, with_model_version=True, model_type="mock"):
    owner = await make_user(db_session)
    chain = await build_chain(
        db_session,
        owner,
        with_model_version=with_model_version,
        model_type=model_type,
    )
    await grant_access(db_session, owner.id, chain["quarry"].id, RoleLevel.USER)

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        resp = await ac.get(
            f"/api/v1/reports/{chain['report'].id}",
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 200
    return resp.json(), chain


@pytest.mark.asyncio
async def test_report_analysis_method_mock(db_session: AsyncSession):
    data, _ = await _get_report(db_session, model_type="mock")
    assert data["analysis_method"] == "mock"
    assert data["model_version_tag"] == "mock-v1"
    assert data["confidence_score"] == pytest.approx(0.87, rel=1e-3)


@pytest.mark.asyncio
async def test_report_analysis_method_real(db_session: AsyncSession):
    data, _ = await _get_report(db_session, model_type="yolo_seg")
    assert data["analysis_method"] == "real"
    assert data["model_version_tag"] == "yolo_seg-v1"


@pytest.mark.asyncio
async def test_report_analysis_method_no_model_version(db_session: AsyncSession):
    # No ModelVersion linked => must fall back to "mock".
    data, _ = await _get_report(db_session, with_model_version=False)
    assert data["analysis_method"] == "mock"
    assert data["model_version_tag"] is None
