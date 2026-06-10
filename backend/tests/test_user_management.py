"""Tests: admin user management (PATCH/DELETE /api/v1/admin/users/{id}).

Also covers the ADMIN-USERS-1 Keycloak-backed endpoints (create, reset-password,
GET access). The Keycloak admin client is fully mocked — no network calls.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel
from app.db.models.audit import AuditLog
from app.db.models.quarry import Quarry
from app.db.models.user import UserProfile
from app.services.keycloak_admin import KeycloakAdminError, get_keycloak_admin_client
from tests.factories import client_for, grant_access, jwt, make_user


async def _admin_user(db_session: AsyncSession) -> UserProfile:
    """A user that is ADMIN on at least one quarry (satisfies require_any_admin)."""
    admin = await make_user(db_session, full_name="Admin User")
    quarry = Quarry(name=f"Quarry {uuid.uuid4()}")
    db_session.add(quarry)
    await db_session.flush()
    await grant_access(db_session, admin.id, quarry.id, RoleLevel.ADMIN)
    return admin


def _fake_kc(*, create_sub: str | None = None, create_error: Exception | None = None):
    """A stand-in KeycloakAdminClient: AsyncMock methods, no network."""
    fake = SimpleNamespace()
    fake.create_user = AsyncMock(
        side_effect=create_error,
        return_value=create_sub or f"kc-sub-{uuid.uuid4()}",
    )
    fake.update_user = AsyncMock(return_value=None)
    fake.reset_password = AsyncMock(return_value=None)
    return fake


@asynccontextmanager
async def _admin_kc(db_session, caller_sub, fake_kc, *, mgmt_enabled: bool = True):
    """Authenticated client with the KC client overridden and the mgmt flag set."""
    from app.main import app

    app.dependency_overrides[get_keycloak_admin_client] = lambda: fake_kc
    with patch(
        "app.routers.admin.get_settings",
        return_value=SimpleNamespace(enable_admin_user_management=mgmt_enabled),
    ):
        # client_for sets get_db and clears all overrides (incl. the KC one) on exit.
        async with client_for(db_session, jwt(caller_sub)) as ac:
            yield ac


# ── POST /admin/users ─────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_create_user_as_admin(db_session: AsyncSession):
    admin = await _admin_user(db_session)
    fake = _fake_kc(create_sub="kc-sub-created")

    async with _admin_kc(db_session, admin.keycloak_sub, fake) as ac:
        resp = await ac.post(
            "/api/v1/admin/users",
            json={"email": "created@example.com", "full_name": "Created User"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["temporary_password"]
    assert body["user"]["email"] == "created@example.com"

    row = (await db_session.execute(
        select(UserProfile).where(UserProfile.email == "created@example.com")
    )).scalar_one()
    assert row.keycloak_sub == "kc-sub-created"
    fake.create_user.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_user_response_excludes_keycloak_sub(db_session: AsyncSession):
    admin = await _admin_user(db_session)
    fake = _fake_kc(create_sub="kc-sub-secret")

    async with _admin_kc(db_session, admin.keycloak_sub, fake) as ac:
        resp = await ac.post(
            "/api/v1/admin/users",
            json={"email": "noleak@example.com", "full_name": "No Leak"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 201
    assert "keycloak_sub" not in resp.json()["user"]
    assert "kc-sub-secret" not in resp.text


@pytest.mark.asyncio
async def test_create_user_audit_excludes_password(db_session: AsyncSession):
    """SEC: the temp password must never reach the audit trail."""
    admin = await _admin_user(db_session)
    fake = _fake_kc(create_sub="kc-sub-audit")

    async with _admin_kc(db_session, admin.keycloak_sub, fake) as ac:
        resp = await ac.post(
            "/api/v1/admin/users",
            json={"email": "audited@example.com", "full_name": "Audited"},
            headers={"Authorization": "Bearer fake"},
        )

    temp = resp.json()["temporary_password"]
    new_user = (await db_session.execute(
        select(UserProfile).where(UserProfile.email == "audited@example.com")
    )).scalar_one()
    log = (await db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_id == new_user.id, AuditLog.action == "user_created"
        )
    )).scalar_one()
    assert log.new_value == {"email": "audited@example.com"}
    assert temp not in str(log.new_value)


@pytest.mark.asyncio
async def test_create_user_duplicate_in_keycloak(db_session: AsyncSession):
    admin = await _admin_user(db_session)
    fake = _fake_kc(create_error=KeycloakAdminError(409, "user exists"))

    async with _admin_kc(db_session, admin.keycloak_sub, fake) as ac:
        resp = await ac.post(
            "/api/v1/admin/users",
            json={"email": "dupe-kc@example.com", "full_name": "Dupe"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 409
    count = (await db_session.execute(
        select(func.count()).select_from(UserProfile).where(
            UserProfile.email == "dupe-kc@example.com"
        )
    )).scalar_one()
    assert count == 0


@pytest.mark.asyncio
async def test_create_user_local_insert_fails_rolls_back_keycloak(db_session: AsyncSession):
    """KC create succeeds but the local mirror collides → orphan KC account disabled."""
    admin = await _admin_user(db_session)
    existing = UserProfile(
        keycloak_sub=f"existing-{uuid.uuid4()}",
        email="collide@example.com",
        full_name="Existing",
    )
    db_session.add(existing)
    await db_session.flush()

    fake = _fake_kc(create_sub="kc-orphan-sub")

    async with _admin_kc(db_session, admin.keycloak_sub, fake) as ac:
        resp = await ac.post(
            "/api/v1/admin/users",
            json={"email": "collide@example.com", "full_name": "Collision"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 409
    fake.update_user.assert_awaited_once_with(sub="kc-orphan-sub", enabled=False)


@pytest.mark.asyncio
async def test_create_user_as_non_admin_forbidden(db_session: AsyncSession):
    plain = await make_user(db_session, full_name="Plain User")
    fake = _fake_kc()

    async with _admin_kc(db_session, plain.keycloak_sub, fake, mgmt_enabled=True) as ac:
        resp = await ac.post(
            "/api/v1/admin/users",
            json={"email": "nope@example.com", "full_name": "Nope"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 403
    fake.create_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_user_flag_off_returns_503(db_session: AsyncSession):
    admin = await _admin_user(db_session)
    fake = _fake_kc()

    async with _admin_kc(db_session, admin.keycloak_sub, fake, mgmt_enabled=False) as ac:
        resp = await ac.post(
            "/api/v1/admin/users",
            json={"email": "dark@example.com", "full_name": "Dark Feature"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 503
    fake.create_user.assert_not_awaited()


# ── PATCH /admin/users/{id} (email/identity sync) ──────────────────────────────
@pytest.mark.asyncio
async def test_patch_email_syncs_to_keycloak(db_session: AsyncSession):
    admin = await _admin_user(db_session)
    target = await make_user(db_session, full_name="Target")
    fake = _fake_kc()

    async with _admin_kc(db_session, admin.keycloak_sub, fake) as ac:
        resp = await ac.patch(
            f"/api/v1/admin/users/{target.id}",
            json={"email": "changed@example.com"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    fake.update_user.assert_awaited_once()
    kwargs = fake.update_user.await_args.kwargs
    assert kwargs["sub"] == target.keycloak_sub
    assert kwargs["email"] == "changed@example.com"

    log = (await db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_id == target.id, AuditLog.action == "user_updated"
        )
    )).scalars().first()
    assert log is not None


@pytest.mark.asyncio
async def test_patch_email_flag_off_returns_503(db_session: AsyncSession):
    """Email is an identity field — refuse to edit it locally when KC can't sync."""
    admin = await _admin_user(db_session)
    target = await make_user(db_session, full_name="Target")
    fake = _fake_kc()

    async with _admin_kc(db_session, admin.keycloak_sub, fake, mgmt_enabled=False) as ac:
        resp = await ac.patch(
            f"/api/v1/admin/users/{target.id}",
            json={"email": "changed@example.com"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 503
    fake.update_user.assert_not_awaited()


# ── POST /admin/users/{id}/reset-password ──────────────────────────────────────
@pytest.mark.asyncio
async def test_reset_password(db_session: AsyncSession):
    admin = await _admin_user(db_session)
    target = await make_user(db_session, full_name="Target")
    fake = _fake_kc()

    async with _admin_kc(db_session, admin.keycloak_sub, fake) as ac:
        resp = await ac.post(
            f"/api/v1/admin/users/{target.id}/reset-password",
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    temp = resp.json()["temporary_password"]
    assert temp
    fake.reset_password.assert_awaited_once()
    assert fake.reset_password.await_args.kwargs["sub"] == target.keycloak_sub

    log = (await db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_id == target.id, AuditLog.action == "user_password_reset"
        )
    )).scalar_one()
    # Password must never be written to the audit trail.
    assert log.new_value is None
    assert temp not in str(log.new_value)


@pytest.mark.asyncio
async def test_reset_password_flag_off_returns_503(db_session: AsyncSession):
    admin = await _admin_user(db_session)
    target = await make_user(db_session, full_name="Target")
    fake = _fake_kc()

    async with _admin_kc(db_session, admin.keycloak_sub, fake, mgmt_enabled=False) as ac:
        resp = await ac.post(
            f"/api/v1/admin/users/{target.id}/reset-password",
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 503
    fake.reset_password.assert_not_awaited()


# ── DELETE /admin/users/{id} (Keycloak disable) ────────────────────────────────
@pytest.mark.asyncio
async def test_deactivate_disables_keycloak_and_blocks_self(db_session: AsyncSession):
    admin = await _admin_user(db_session)
    target = await make_user(db_session, full_name="Target")
    fake = _fake_kc()

    async with _admin_kc(db_session, admin.keycloak_sub, fake) as ac:
        resp = await ac.delete(
            f"/api/v1/admin/users/{target.id}",
            headers={"Authorization": "Bearer fake"},
        )
        self_resp = await ac.delete(
            f"/api/v1/admin/users/{admin.id}",
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 204
    fake.update_user.assert_awaited_once_with(sub=target.keycloak_sub, enabled=False)
    # Self-deactivation is blocked before any Keycloak call.
    assert self_resp.status_code == 400
    assert fake.update_user.await_count == 1


# ── GET /admin/users/{id}/access ───────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_user_access(db_session: AsyncSession):
    admin = await _admin_user(db_session)
    target = await make_user(db_session, full_name="Target")
    now = datetime.now(tz=timezone.utc)

    active_quarry = Quarry(name="Alpha Quarry")
    deleted_quarry = Quarry(name="Beta Quarry", deleted_at=now)
    revoked_quarry = Quarry(name="Gamma Quarry")
    db_session.add_all([active_quarry, deleted_quarry, revoked_quarry])
    await db_session.flush()

    await grant_access(db_session, target.id, active_quarry.id, RoleLevel.BLASTER)
    await grant_access(db_session, target.id, deleted_quarry.id, RoleLevel.SURVEYOR)
    revoked = await grant_access(db_session, target.id, revoked_quarry.id, RoleLevel.ADMIN)
    revoked.revoked_at = now
    await db_session.flush()

    async with client_for(db_session, jwt(admin.keycloak_sub)) as ac:
        resp = await ac.get(
            f"/api/v1/admin/users/{target.id}/access",
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1  # excludes soft-deleted quarry + revoked access
    entry = data[0]
    assert entry["quarry_name"] == "Alpha Quarry"
    assert entry["role_level"] == int(RoleLevel.BLASTER)
    assert "access_id" in entry


@pytest.mark.asyncio
async def test_get_user_access_as_non_admin_forbidden(db_session: AsyncSession):
    plain = await make_user(db_session, full_name="Plain")
    target = await make_user(db_session, full_name="Target")

    async with client_for(db_session, jwt(plain.keycloak_sub)) as ac:
        resp = await ac.get(
            f"/api/v1/admin/users/{target.id}/access",
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 403


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


@pytest.mark.asyncio
async def test_user_response_excludes_keycloak_sub(db_session: AsyncSession):
    """SEC-2 (security.md): keycloak_sub must never be exposed in API responses."""
    admin = await _admin_user(db_session)
    target = await make_user(db_session, full_name="Old Name")

    async with client_for(db_session, jwt(admin.keycloak_sub)) as ac:
        list_resp = await ac.get(
            "/api/v1/admin/users", headers={"Authorization": "Bearer fake"}
        )
        patch_resp = await ac.patch(
            f"/api/v1/admin/users/{target.id}",
            json={"full_name": "New Name"},
            headers={"Authorization": "Bearer fake"},
        )

    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert items, "expected at least one user in the list"
    assert all("keycloak_sub" not in item for item in items)
    assert patch_resp.status_code == 200
    assert "keycloak_sub" not in patch_resp.json()
