"""Tests: dev-seed guard (SEC-3)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import client_for, jwt


@pytest.mark.asyncio
async def test_dev_seed_disabled(db_session: AsyncSession):
    """Default enable_dev_seed=False makes the endpoint return 404 (undiscoverable)."""
    sub = f"caller-{uuid.uuid4()}"
    with patch(
        "app.routers.admin.get_settings",
        return_value=SimpleNamespace(enable_dev_seed=False),
    ):
        async with client_for(db_session, jwt(sub)) as ac:
            resp = await ac.post(
                "/api/v1/admin/dev-seed", headers={"Authorization": "Bearer fake"}
            )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_dev_seed_enabled(db_session: AsyncSession):
    """With the flag on, the bootstrap endpoint works (201) for any authed caller."""
    sub = f"caller-{uuid.uuid4()}"
    with patch(
        "app.routers.admin.get_settings",
        return_value=SimpleNamespace(enable_dev_seed=True),
    ):
        async with client_for(db_session, jwt(sub)) as ac:
            resp = await ac.post(
                "/api/v1/admin/dev-seed", headers={"Authorization": "Bearer fake"}
            )

    assert resp.status_code == 201
    assert resp.json()["report_id"]
