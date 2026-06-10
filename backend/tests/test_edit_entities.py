"""EDIT-1: PATCH-редактирование сущностей + AuditLog на каждое изменение."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel
from app.db.models.audit import AuditLog
from app.db.models.passport import BlastPassport, PassportStatus
from tests.factories import build_chain, client_for, grant_access, jwt, make_user


async def _audit_rows(db: AsyncSession, entity_type: str, entity_id) -> list[AuditLog]:
    rows = (await db.execute(
        select(AuditLog).where(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id,
            AuditLog.action == "entity_updated",
        )
    )).scalars().all()
    return list(rows)


@pytest.mark.asyncio
async def test_patch_quarry_writes_audit(db_session: AsyncSession):
    owner = await make_user(db_session)
    chain = await build_chain(db_session, owner)
    await grant_access(db_session, owner.id, chain["quarry"].id, RoleLevel.ADMIN)

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        resp = await ac.patch(
            f"/api/v1/quarries/{chain['quarry'].id}",
            json={"location_description": "новая локация"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    assert resp.json()["location_description"] == "новая локация"
    rows = await _audit_rows(db_session, "quarry", chain["quarry"].id)
    assert len(rows) == 1
    assert rows[0].old_value == {"location_description": "test"}
    assert rows[0].new_value == {"location_description": "новая локация"}


@pytest.mark.asyncio
async def test_patch_quarry_requires_admin(db_session: AsyncSession):
    owner = await make_user(db_session)
    chain = await build_chain(db_session, owner)
    await grant_access(db_session, owner.id, chain["quarry"].id, RoleLevel.BLASTER)

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        resp = await ac.patch(
            f"/api/v1/quarries/{chain['quarry'].id}",
            json={"name": "hack"},
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_patch_section_writes_audit(db_session: AsyncSession):
    owner = await make_user(db_session)
    chain = await build_chain(db_session, owner)
    await grant_access(db_session, owner.id, chain["quarry"].id, RoleLevel.BLASTER)

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        resp = await ac.patch(
            f"/api/v1/quarries/{chain['quarry'].id}/sections/{chain['section'].id}",
            json={"name": "Блок А-2", "block_number": "A-2"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    assert resp.json()["name"] == "Блок А-2"
    rows = await _audit_rows(db_session, "site_section", chain["section"].id)
    assert len(rows) == 1
    assert rows[0].old_value["block_number"] == "A-1"


@pytest.mark.asyncio
async def test_patch_device_and_calibration(db_session: AsyncSession):
    owner = await make_user(db_session)
    chain = await build_chain(db_session, owner)
    await grant_access(db_session, owner.id, chain["quarry"].id, RoleLevel.SURVEYOR)
    device = chain["capture_session"].device_id
    calibration = chain["capture_session"].calibration_id

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        dev_resp = await ac.patch(
            f"/api/v1/devices/{device}",
            json={"notes": "перепрошита", "firmware_version": "1.2.3"},
            headers={"Authorization": "Bearer fake"},
        )
        cal_resp = await ac.patch(
            f"/api/v1/devices/{device}/calibrations/{calibration}",
            json={"is_active": False},
            headers={"Authorization": "Bearer fake"},
        )

    assert dev_resp.status_code == 200
    assert dev_resp.json()["firmware_version"] == "1.2.3"
    assert cal_resp.status_code == 200
    assert cal_resp.json()["is_active"] is False
    assert len(await _audit_rows(db_session, "device", device)) == 1
    assert len(await _audit_rows(db_session, "calibration", calibration)) == 1


@pytest.mark.asyncio
async def test_patch_device_cannot_change_serial(db_session: AsyncSession):
    """serial_number — идентичность устройства; PATCH его молча игнорирует."""
    owner = await make_user(db_session)
    chain = await build_chain(db_session, owner)
    device_id = chain["capture_session"].device_id

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        before = await ac.get(
            f"/api/v1/devices/{device_id}", headers={"Authorization": "Bearer fake"}
        )
        resp = await ac.patch(
            f"/api/v1/devices/{device_id}",
            json={"serial_number": "FAKE-123", "notes": "ok"},
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 200
    assert resp.json()["serial_number"] == before.json()["serial_number"]


@pytest.mark.asyncio
async def test_patch_blast_event_writes_audit(db_session: AsyncSession):
    owner = await make_user(db_session)
    chain = await build_chain(db_session, owner)
    await grant_access(db_session, owner.id, chain["quarry"].id, RoleLevel.BLASTER)

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        resp = await ac.patch(
            f"/api/v1/quarries/{chain['quarry'].id}/passports/{chain['passport'].id}/blast-event",
            json={"actual_explosive_kg": 2500.5, "weather_conditions": "ясно"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    assert float(resp.json()["actual_explosive_kg"]) == 2500.5
    rows = await _audit_rows(db_session, "blast_event", chain["blast_event"].id)
    assert len(rows) == 1
    assert rows[0].passport_id == chain["passport"].id


@pytest.mark.asyncio
async def test_patch_passport_draft_only(db_session: AsyncSession):
    """DRAFT редактируется (с аудитом); ACTIVE — только ревизией → 409."""
    owner = await make_user(db_session)
    chain = await build_chain(db_session, owner)  # passport ACTIVE
    await grant_access(db_session, owner.id, chain["quarry"].id, RoleLevel.BLASTER)

    draft = BlastPassport(
        site_section_id=chain["section"].id,
        created_by_id=owner.id,
        explosive_type="ANFO",
        total_explosive_kg=100.0,
        status=PassportStatus.DRAFT,
    )
    db_session.add(draft)
    await db_session.flush()

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        ok = await ac.patch(
            f"/api/v1/quarries/{chain['quarry'].id}/passports/{draft.id}",
            json={"target_p80_mm": 500.0},
            headers={"Authorization": "Bearer fake"},
        )
        blocked = await ac.patch(
            f"/api/v1/quarries/{chain['quarry'].id}/passports/{chain['passport'].id}",
            json={"target_p80_mm": 1.0},
            headers={"Authorization": "Bearer fake"},
        )

    assert ok.status_code == 200
    assert float(ok.json()["target_p80_mm"]) == 500.0
    assert blocked.status_code == 409
    rows = await _audit_rows(db_session, "blast_passport", draft.id)
    assert len(rows) == 1
