"""
Test configuration and shared fixtures.

Uses SQLite in-memory for fast tests. Patches decode_token to skip Keycloak.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
_TestSessionLocal = async_sessionmaker(_test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once per test session."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _TestSessionLocal() as session:
        yield session
        await session.rollback()


def make_jwt_payload(
    sub: str = "test-sub-001",
    email: str = "test@zmetrics.local",
    roles: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "sub": sub,
        "email": email,
        "name": "Test User",
        "preferred_username": email,
        "realm_access": {"roles": roles or ["zmetrics-user"]},
    }


@pytest.fixture
def mock_admin_token() -> dict[str, str]:
    return make_jwt_payload(roles=["zmetrics-admin"])


@pytest.fixture
def mock_blaster_token() -> dict[str, str]:
    return make_jwt_payload(roles=["zmetrics-blaster"])


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """AsyncClient with overridden DB dependency and mocked JWT."""
    from app.db.session import get_db
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.auth.jwt.decode_token", new_callable=AsyncMock) as mock_decode:
        mock_decode.return_value = make_jwt_payload(roles=["zmetrics-admin"])
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()
