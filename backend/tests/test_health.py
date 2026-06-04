"""Smoke test: health endpoint."""

import pytest


@pytest.mark.asyncio
async def test_health_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    # DB may not have Redis in CI; just check the endpoint responds
    assert data["status"] in ("ok", "degraded")


@pytest.mark.asyncio
async def test_health_ready(client):
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
