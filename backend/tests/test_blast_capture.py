"""Tests: Device, BlastEvent, CaptureSession, and Artifact upload."""

from __future__ import annotations

import io
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.blast import BlastEvent, Calibration, Device
from app.db.models.capture import CaptureSession
from app.db.models.passport import BlastPassport, PassportStatus
from app.db.models.quarry import Quarry, SiteSection
from app.db.models.user import QuarryUserAccess, Role, UserProfile


# ── helpers ───────────────────────────────────────────────────────────────────


def _jwt(sub: str, email: str = "u@test.local") -> dict:
    return {"sub": sub, "email": email, "name": "Test User", "realm_access": {"roles": []}}


@asynccontextmanager
async def _client(db_session: AsyncSession, jwt_payload: dict):
    from app.db.session import get_db
    from app.main import app

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    try:
        with patch("app.dependencies.decode_token", new_callable=AsyncMock) as mock_decode:
            mock_decode.return_value = jwt_payload
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                yield ac
    finally:
        app.dependency_overrides.clear()


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def blaster_user(db_session: AsyncSession):
    """User + quarry + section + blaster role + access + approved passport."""
    sub = f"blaster-{uuid.uuid4()}"
    quarry = Quarry(name="Blast Quarry")
    db_session.add(quarry)
    await db_session.flush()

    section = SiteSection(quarry_id=quarry.id, name="Block B", block_number="B1")
    db_session.add(section)

    role = Role(name=f"blaster-{uuid.uuid4()}", level=3)
    db_session.add(role)
    await db_session.flush()

    user = UserProfile(keycloak_sub=sub, email=f"{sub}@test.local", full_name="Blaster User")
    db_session.add(user)
    await db_session.flush()

    access = QuarryUserAccess(user_id=user.id, quarry_id=quarry.id, role_id=role.id)
    db_session.add(access)

    passport = BlastPassport(
        site_section_id=section.id,
        created_by_id=user.id,
        explosive_type="ANFO",
        total_explosive_kg=500.0,
        status=PassportStatus.APPROVED,
    )
    db_session.add(passport)
    await db_session.flush()

    return {
        "sub": sub,
        "user": user,
        "quarry": quarry,
        "section": section,
        "role": role,
        "passport": passport,
    }


@pytest_asyncio.fixture
async def surveyor_user(db_session: AsyncSession, blaster_user):
    """Surveyor-level user on the same quarry."""
    sub = f"surveyor-{uuid.uuid4()}"
    role = Role(name=f"surveyor-{uuid.uuid4()}", level=2)
    db_session.add(role)
    await db_session.flush()

    user = UserProfile(
        keycloak_sub=sub, email=f"{sub}@test.local", full_name="Surveyor User"
    )
    db_session.add(user)
    await db_session.flush()

    access = QuarryUserAccess(
        user_id=user.id, quarry_id=blaster_user["quarry"].id, role_id=role.id
    )
    db_session.add(access)
    await db_session.flush()

    return {"sub": sub, "user": user, **blaster_user}


@pytest_asyncio.fixture
async def device_and_calibration(db_session: AsyncSession, blaster_user):
    """A registered Device + active Calibration."""
    device = Device(serial_number=f"SN-{uuid.uuid4()}", model="ZED 2")
    db_session.add(device)
    await db_session.flush()

    cal = Calibration(
        device_id=device.id,
        calibrated_by_id=blaster_user["user"].id,
        left_camera_matrix={"fx": 700.0, "fy": 700.0, "cx": 640.0, "cy": 360.0},
        right_camera_matrix={"fx": 700.0, "fy": 700.0, "cx": 640.0, "cy": 360.0},
        left_dist_coeffs={"k1": 0.0, "k2": 0.0, "p1": 0.0, "p2": 0.0, "k3": 0.0},
        right_dist_coeffs={"k1": 0.0, "k2": 0.0, "p1": 0.0, "p2": 0.0, "k3": 0.0},
        rotation_matrix={"data": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]},
        translation_vector={"data": [0.12, 0.0, 0.0]},
        baseline_mm=120.0,
        image_width_px=1280,
        image_height_px=720,
    )
    db_session.add(cal)
    await db_session.flush()

    return {"device": device, "calibration": cal}


@pytest_asyncio.fixture
async def blast_event(db_session: AsyncSession, blaster_user):
    """BlastEvent linked to the blaster_user fixture's passport."""
    event = BlastEvent(
        passport_id=blaster_user["passport"].id,
        executed_by_id=blaster_user["user"].id,
        blast_datetime=datetime.now(tz=timezone.utc),
        actual_explosive_kg=480.0,
    )
    db_session.add(event)
    await db_session.flush()
    return event


@pytest_asyncio.fixture
async def capture_session(db_session: AsyncSession, blaster_user, blast_event, device_and_calibration):
    """CaptureSession linked to the blast_event fixture."""
    session = CaptureSession(
        blast_event_id=blast_event.id,
        device_id=device_and_calibration["device"].id,
        calibration_id=device_and_calibration["calibration"].id,
        captured_by_id=blaster_user["user"].id,
        capture_datetime=datetime.now(tz=timezone.utc),
    )
    db_session.add(session)
    await db_session.flush()
    return session


# ── Device tests ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_device(db_session: AsyncSession, blaster_user):
    async with _client(db_session, _jwt(blaster_user["sub"])) as ac:
        resp = await ac.post(
            "/api/v1/devices",
            json={"serial_number": f"SN-{uuid.uuid4()}", "model": "ZED 2"},
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["model"] == "ZED 2"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_devices(db_session: AsyncSession, blaster_user, device_and_calibration):
    async with _client(db_session, _jwt(blaster_user["sub"])) as ac:
        resp = await ac.get("/api/v1/devices", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200
    data = resp.json()
    ids = [d["id"] for d in data["items"]]
    assert str(device_and_calibration["device"].id) in ids


@pytest.mark.asyncio
async def test_add_calibration(db_session: AsyncSession, blaster_user, device_and_calibration):
    device = device_and_calibration["device"]
    payload = {
        "left_camera_matrix": {"fx": 700.0, "fy": 700.0, "cx": 640.0, "cy": 360.0},
        "right_camera_matrix": {"fx": 700.0, "fy": 700.0, "cx": 640.0, "cy": 360.0},
        "left_dist_coeffs": {"k1": 0.0, "k2": 0.0, "p1": 0.0, "p2": 0.0, "k3": 0.0},
        "right_dist_coeffs": {"k1": 0.0, "k2": 0.0, "p1": 0.0, "p2": 0.0, "k3": 0.0},
        "rotation_matrix": {"data": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]},
        "translation_vector": {"data": [0.12, 0.0, 0.0]},
        "baseline_mm": 120.0,
        "image_width_px": 1280,
        "image_height_px": 720,
    }
    async with _client(db_session, _jwt(blaster_user["sub"])) as ac:
        resp = await ac.post(
            f"/api/v1/devices/{device.id}/calibrations",
            json=payload,
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 201
    assert resp.json()["device_id"] == str(device.id)


# ── BlastEvent tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_blast_event(db_session: AsyncSession, blaster_user):
    q_id = blaster_user["quarry"].id
    p_id = blaster_user["passport"].id
    payload = {
        "blast_datetime": datetime.now(tz=timezone.utc).isoformat(),
        "actual_explosive_kg": 490.0,
        "notes": "Test blast",
    }
    async with _client(db_session, _jwt(blaster_user["sub"])) as ac:
        resp = await ac.post(
            f"/api/v1/quarries/{q_id}/passports/{p_id}/blast-event",
            json=payload,
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["passport_id"] == str(p_id)
    assert data["notes"] == "Test blast"


@pytest.mark.asyncio
async def test_create_blast_event_draft_passport_rejected(
    db_session: AsyncSession, blaster_user
):
    """A blast event cannot be created for a DRAFT passport."""
    draft_passport = BlastPassport(
        site_section_id=blaster_user["section"].id,
        created_by_id=blaster_user["user"].id,
        explosive_type="ANFO",
        total_explosive_kg=100.0,
        status=PassportStatus.DRAFT,
    )
    db_session.add(draft_passport)
    await db_session.flush()

    q_id = blaster_user["quarry"].id
    async with _client(db_session, _jwt(blaster_user["sub"])) as ac:
        resp = await ac.post(
            f"/api/v1/quarries/{q_id}/passports/{draft_passport.id}/blast-event",
            json={"blast_datetime": datetime.now(tz=timezone.utc).isoformat()},
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_blast_event_duplicate_rejected(
    db_session: AsyncSession, blaster_user, blast_event
):
    """Second blast event for the same passport → 409."""
    q_id = blaster_user["quarry"].id
    p_id = blaster_user["passport"].id
    async with _client(db_session, _jwt(blaster_user["sub"])) as ac:
        resp = await ac.post(
            f"/api/v1/quarries/{q_id}/passports/{p_id}/blast-event",
            json={"blast_datetime": datetime.now(tz=timezone.utc).isoformat()},
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_blast_event(db_session: AsyncSession, blaster_user, blast_event):
    q_id = blaster_user["quarry"].id
    p_id = blaster_user["passport"].id
    async with _client(db_session, _jwt(blaster_user["sub"])) as ac:
        resp = await ac.get(
            f"/api/v1/quarries/{q_id}/passports/{p_id}/blast-event",
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 200
    assert resp.json()["id"] == str(blast_event.id)


# ── CaptureSession tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_capture_session(
    db_session: AsyncSession, surveyor_user, blast_event, device_and_calibration
):
    q_id = surveyor_user["quarry"].id
    p_id = surveyor_user["passport"].id
    payload = {
        "device_id": str(device_and_calibration["device"].id),
        "calibration_id": str(device_and_calibration["calibration"].id),
        "capture_datetime": datetime.now(tz=timezone.utc).isoformat(),
        "notes": "Morning capture",
    }
    async with _client(db_session, _jwt(surveyor_user["sub"])) as ac:
        resp = await ac.post(
            f"/api/v1/quarries/{q_id}/passports/{p_id}/blast-event/capture-sessions",
            json=payload,
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["blast_event_id"] == str(blast_event.id)
    assert data["frame_count"] == 0


@pytest.mark.asyncio
async def test_list_capture_sessions(
    db_session: AsyncSession, blaster_user, blast_event, capture_session
):
    q_id = blaster_user["quarry"].id
    p_id = blaster_user["passport"].id
    async with _client(db_session, _jwt(blaster_user["sub"])) as ac:
        resp = await ac.get(
            f"/api/v1/quarries/{q_id}/passports/{p_id}/blast-event/capture-sessions",
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 200
    data = resp.json()
    ids = [s["id"] for s in data["items"]]
    assert str(capture_session.id) in ids


# ── Artifact upload tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_artifact(db_session: AsyncSession, blaster_user, capture_session):
    mock_storage = MagicMock()
    mock_storage.upload_file.return_value = "some/key"

    with patch("app.routers.capture_sessions.get_storage_service", return_value=mock_storage):
        async with _client(db_session, _jwt(blaster_user["sub"])) as ac:
            resp = await ac.post(
                f"/api/v1/capture-sessions/{capture_session.id}/artifacts",
                data={"artifact_type": "left_frame", "frame_index": "0"},
                files={"file": ("frame_0.jpg", io.BytesIO(b'\xff\xd8\xff' + b"fake-jpeg-data"), "image/jpeg")},
                headers={"Authorization": "Bearer fake"},
            )

    assert resp.status_code == 201
    data = resp.json()
    assert data["artifact_type"] == "left_frame"
    assert data["file_size_bytes"] == len(b'\xff\xd8\xff' + b"fake-jpeg-data")
    assert data["frame_index"] == 0
    assert data["content_type"] == "image/jpeg"
    mock_storage.upload_file.assert_called_once()


@pytest.mark.asyncio
async def test_upload_artifact_wrong_content_type_rejected(
    db_session: AsyncSession, blaster_user, capture_session
):
    """Uploading a PDF as a left_frame → 415."""
    mock_storage = MagicMock()

    with patch("app.routers.capture_sessions.get_storage_service", return_value=mock_storage):
        async with _client(db_session, _jwt(blaster_user["sub"])) as ac:
            resp = await ac.post(
                f"/api/v1/capture-sessions/{capture_session.id}/artifacts",
                data={"artifact_type": "left_frame"},
                files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
                headers={"Authorization": "Bearer fake"},
            )

    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_list_artifacts(db_session: AsyncSession, blaster_user, capture_session):
    from app.db.models.artifact import Artifact, ArtifactType

    artifact = Artifact(
        capture_session_id=capture_session.id,
        artifact_type=ArtifactType.LEFT_FRAME,
        storage_bucket="zmetrics-frames",
        storage_key=f"sessions/{capture_session.id}/left_frame/test.jpg",
        file_size_bytes=1024,
        content_type="image/jpeg",
    )
    db_session.add(artifact)
    await db_session.flush()

    async with _client(db_session, _jwt(blaster_user["sub"])) as ac:
        resp = await ac.get(
            f"/api/v1/capture-sessions/{capture_session.id}/artifacts",
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) >= 1


@pytest.mark.asyncio
async def test_get_artifact_url(db_session: AsyncSession, blaster_user, capture_session):
    from app.db.models.artifact import Artifact, ArtifactType

    artifact = Artifact(
        capture_session_id=capture_session.id,
        artifact_type=ArtifactType.LEFT_FRAME,
        storage_bucket="zmetrics-frames",
        storage_key="sessions/test/left_frame/x.jpg",
        file_size_bytes=512,
        content_type="image/jpeg",
    )
    db_session.add(artifact)
    await db_session.flush()

    mock_storage = MagicMock()
    mock_storage.get_presigned_url.return_value = "https://minio.test/presigned"

    with patch("app.routers.capture_sessions.get_storage_service", return_value=mock_storage):
        async with _client(db_session, _jwt(blaster_user["sub"])) as ac:
            resp = await ac.get(
                f"/api/v1/capture-sessions/{capture_session.id}/artifacts/{artifact.id}/url",
                headers={"Authorization": "Bearer fake"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["url"] == "https://minio.test/presigned"
    assert data["expires_in"] == 3600


# ── CAP-MULTI: frame series + per-pair jobs + capture summary ─────────────────


def _add_frame(db_session, session_id, artifact_type, frame_index):
    from app.db.models.artifact import Artifact

    db_session.add(Artifact(
        capture_session_id=session_id,
        artifact_type=artifact_type,
        storage_bucket="zmetrics-frames",
        storage_key=f"sessions/{session_id}/{artifact_type.value}/{frame_index}.jpg",
        file_size_bytes=10,
        content_type="image/jpeg",
        frame_index=frame_index,
    ))


@pytest.mark.asyncio
async def test_enqueue_job_per_frame_pair(
    db_session: AsyncSession, surveyor_user, capture_session
):
    """Серия пар в одной сессии: job создаётся на конкретную пару (frame_index)."""
    from app.db.models.artifact import ArtifactType

    for idx in (0, 1):
        _add_frame(db_session, capture_session.id, ArtifactType.LEFT_FRAME, idx)
        _add_frame(db_session, capture_session.id, ArtifactType.RIGHT_FRAME, idx)
    await db_session.flush()

    with patch("app.services.analysis.celery_app") as celery_mock:
        celery_mock.send_task.return_value = MagicMock(id="task-1")
        async with _client(db_session, _jwt(surveyor_user["sub"])) as ac:
            r0 = await ac.post(
                f"/api/v1/captures/{capture_session.id}/jobs",
                json={"frame_index": 0},
                headers={"Authorization": "Bearer fake"},
            )
            r1 = await ac.post(
                f"/api/v1/captures/{capture_session.id}/jobs",
                json={"frame_index": 1},
                headers={"Authorization": "Bearer fake"},
            )

    assert r0.status_code == 201 and r1.status_code == 201
    assert r0.json()["frame_index"] == 0
    assert r1.json()["frame_index"] == 1
    assert r0.json()["id"] != r1.json()["id"]


@pytest.mark.asyncio
async def test_enqueue_job_missing_frame_pair_rejected(
    db_session: AsyncSession, surveyor_user, capture_session
):
    """Job на пару, которой нет в сессии → 409, а не тихий пустой анализ."""
    from app.db.models.artifact import ArtifactType

    _add_frame(db_session, capture_session.id, ArtifactType.LEFT_FRAME, 0)
    await db_session.flush()

    with patch("app.services.analysis.celery_app") as celery_mock:
        celery_mock.send_task.return_value = MagicMock(id="task-1")
        async with _client(db_session, _jwt(surveyor_user["sub"])) as ac:
            resp = await ac.post(
                f"/api/v1/captures/{capture_session.id}/jobs",
                json={"frame_index": 5},
                headers={"Authorization": "Bearer fake"},
            )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_capture_summary_aggregates(
    db_session: AsyncSession, blaster_user, blast_event, capture_session
):
    """Сводка по взрыву: пары кадров, статусы джобов, имя снявшего."""
    from app.db.models.analysis import AnalysisJob, JobStatus
    from app.db.models.artifact import ArtifactType

    _add_frame(db_session, capture_session.id, ArtifactType.LEFT_FRAME, 0)
    _add_frame(db_session, capture_session.id, ArtifactType.RIGHT_FRAME, 0)
    _add_frame(db_session, capture_session.id, ArtifactType.LEFT_FRAME, 1)
    db_session.add(AnalysisJob(
        capture_session_id=capture_session.id,
        status=JobStatus.COMPLETED,
        frame_index=0,
    ))
    db_session.add(AnalysisJob(
        capture_session_id=capture_session.id,
        status=JobStatus.FAILED,
        frame_index=1,
    ))
    await db_session.flush()

    q_id = blaster_user["quarry"].id
    p_id = blaster_user["passport"].id
    async with _client(db_session, _jwt(blaster_user["sub"])) as ac:
        resp = await ac.get(
            f"/api/v1/quarries/{q_id}/passports/{p_id}/blast-event/capture-summary",
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    rows = resp.json()
    row = next(r for r in rows if r["id"] == str(capture_session.id))
    assert row["captured_by_name"] == "Blaster User"
    assert row["jobs_total"] == 2
    assert row["jobs_completed"] == 1
    assert row["jobs_failed"] == 1
    frames = {f["frame_index"]: f for f in row["frames"]}
    assert frames[0]["has_left"] and frames[0]["has_right"]
    assert frames[0]["job_status"] == "completed"
    assert frames[1]["has_left"] and not frames[1]["has_right"]
    assert frames[1]["job_status"] == "failed"


# ── Security tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_capture_session_upload_no_access(db_session: AsyncSession, capture_session):
    """User with no quarry access cannot upload an artifact → 403."""
    no_access_sub = f"no-access-{uuid.uuid4()}"
    user = UserProfile(
        keycloak_sub=no_access_sub,
        email=f"{no_access_sub}@test.local",
        full_name="No Access User",
    )
    db_session.add(user)
    await db_session.flush()

    mock_storage = MagicMock()
    with patch("app.routers.capture_sessions.get_storage_service", return_value=mock_storage):
        async with _client(db_session, _jwt(no_access_sub)) as ac:
            resp = await ac.post(
                f"/api/v1/capture-sessions/{capture_session.id}/artifacts",
                data={"artifact_type": "left_frame"},
                files={"file": ("frame.jpg", io.BytesIO(b'\xff\xd8\xff' + b"data"), "image/jpeg")},
                headers={"Authorization": "Bearer fake"},
            )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_capture_session_artifact_wrong_quarry(db_session: AsyncSession, capture_session):
    """Surveyor on quarry A cannot upload to a session in quarry B → 403."""
    wrong_sub = f"wrong-{uuid.uuid4()}"
    wrong_quarry = Quarry(name=f"Wrong Quarry {uuid.uuid4()}")
    db_session.add(wrong_quarry)
    wrong_role = Role(name=f"surveyor-{uuid.uuid4()}", level=2)
    db_session.add(wrong_role)
    await db_session.flush()

    wrong_user = UserProfile(
        keycloak_sub=wrong_sub, email=f"{wrong_sub}@test.local", full_name="Wrong User"
    )
    db_session.add(wrong_user)
    await db_session.flush()

    db_session.add(QuarryUserAccess(
        user_id=wrong_user.id, quarry_id=wrong_quarry.id, role_id=wrong_role.id
    ))
    await db_session.flush()

    mock_storage = MagicMock()
    with patch("app.routers.capture_sessions.get_storage_service", return_value=mock_storage):
        async with _client(db_session, _jwt(wrong_sub)) as ac:
            resp = await ac.post(
                f"/api/v1/capture-sessions/{capture_session.id}/artifacts",
                data={"artifact_type": "left_frame"},
                files={"file": ("frame.jpg", io.BytesIO(b'\xff\xd8\xff' + b"data"), "image/jpeg")},
                headers={"Authorization": "Bearer fake"},
            )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_blast_event_passport_wrong_quarry(db_session: AsyncSession, blaster_user):
    """GET blast-event with passport_id from a different quarry → 404."""
    other_quarry = Quarry(name=f"Other Quarry {uuid.uuid4()}")
    db_session.add(other_quarry)
    await db_session.flush()

    other_section = SiteSection(
        quarry_id=other_quarry.id, name="Other Block", block_number="OB-1"
    )
    db_session.add(other_section)
    await db_session.flush()

    other_passport = BlastPassport(
        site_section_id=other_section.id,
        created_by_id=blaster_user["user"].id,
        explosive_type="ANFO",
        total_explosive_kg=100.0,
        status=PassportStatus.APPROVED,
    )
    db_session.add(other_passport)
    await db_session.flush()

    q_id = blaster_user["quarry"].id
    async with _client(db_session, _jwt(blaster_user["sub"])) as ac:
        resp = await ac.get(
            f"/api/v1/quarries/{q_id}/passports/{other_passport.id}/blast-event",
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_analysis_job_result_wrong_session(db_session: AsyncSession):
    """GET job result using a job_id from a different capture session → 404."""
    from app.auth.roles import RoleLevel
    from tests.factories import build_chain, client_for, grant_access, jwt, make_user

    owner = await make_user(db_session)
    chain_a = await build_chain(db_session, owner)
    await grant_access(db_session, owner.id, chain_a["quarry"].id, RoleLevel.USER)

    chain_b = await build_chain(db_session, owner)

    async with client_for(db_session, jwt(owner.keycloak_sub)) as ac:
        resp = await ac.get(
            f"/api/v1/capture-sessions/{chain_a['capture_session'].id}"
            f"/jobs/{chain_b['job'].id}/result",
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 404
