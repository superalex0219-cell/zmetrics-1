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


# ── REPORT-X: форматы PDF/DOCX/XLSX/CSV ───────────────────────────────────────


class _FakeStorage:
    """Без MinIO: download_bytes падает (картинок нет), upload_file — no-op."""

    def __init__(self) -> None:
        self.uploaded: list[str] = []

    def download_bytes(self, bucket: str, key: str) -> bytes:
        raise FileNotFoundError(key)

    def upload_file(self, bucket: str, key: str, file_obj, content_type="") -> str:
        self.uploaded.append(key)
        return key


@pytest.fixture()
def fake_storage(monkeypatch) -> _FakeStorage:
    storage = _FakeStorage()
    monkeypatch.setattr("app.services.storage.get_storage_service", lambda: storage)
    return storage


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("fmt", "content_type", "magic"),
    [
        ("pdf", "application/pdf", b"%PDF"),
        ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK"),
        ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", b"PK"),
        ("csv", "text/csv", b"\xef\xbb\xbf"),  # utf-8-sig BOM
    ],
)
async def test_export_formats(db_session: AsyncSession, fake_storage, fmt, content_type, magic):
    owner = await make_user(db_session)
    chain = await build_chain(db_session, owner)
    await grant_access(db_session, owner.id, chain["quarry"].id, RoleLevel.BLASTER)

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        resp = await ac.get(
            f"/api/v1/reports/{chain['report'].id}/export",
            params={"format": fmt},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith(content_type)
    assert resp.content.startswith(magic)
    assert f".{fmt}" in resp.headers["content-disposition"]
    # STORE-1: файл отчёта сохранён в MinIO
    assert fake_storage.uploaded == [f"reports/{chain['report'].id}/report.{fmt}"]


@pytest.mark.asyncio
async def test_export_unknown_format_is_400(db_session: AsyncSession, fake_storage):
    owner = await make_user(db_session)
    chain = await build_chain(db_session, owner)
    await grant_access(db_session, owner.id, chain["quarry"].id, RoleLevel.BLASTER)

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        resp = await ac.get(
            f"/api/v1/reports/{chain['report'].id}/export",
            params={"format": "odt"},
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_export_json_includes_passport_and_method(db_session: AsyncSession, fake_storage):
    """REPORT-X: JSON несёт паспорт БВР, карьер/взрыв и метод анализа."""
    owner = await make_user(db_session)
    chain = await build_chain(db_session, owner)
    await grant_access(db_session, owner.id, chain["quarry"].id, RoleLevel.BLASTER)

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        resp = await ac.get(
            f"/api/v1/reports/{chain['report'].id}/export",
            headers={"Authorization": "Bearer fake"},
        )

    payload = json.loads(resp.content)
    assert payload["passport"]["explosive_type"] == "ANFO"
    assert payload["quarry"]["name"].startswith("Quarry")
    assert payload["method"]["analysis_method"] in ("mock", "real")
    assert payload["blast_event"]["blast_datetime"]
    assert payload["recommendations"][0]["status_ru"]
