"""Shared builders for endpoint tests.

Mirrors the inline helpers in test_blast_capture.py but factored out so the
report/analysis-result/me/admin suites can each build a full entity chain and
an authenticated client without copy-pasting.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analysis import AnalysisJob, AnalysisResult, JobStatus, ModelVersion
from app.db.models.blast import BlastEvent, Calibration, Device
from app.db.models.capture import CaptureSession
from app.db.models.passport import BlastPassport, PassportStatus
from app.db.models.quarry import Quarry, SiteSection
from app.db.models.report import Recommendation, Report
from app.db.models.user import QuarryUserAccess, Role, UserProfile


def jwt(sub: str, email: str = "u@test.local") -> dict:
    return {"sub": sub, "email": email, "name": "Test User", "realm_access": {"roles": []}}


@asynccontextmanager
async def client_for(db_session: AsyncSession, jwt_payload: dict):
    """AsyncClient bound to db_session, with decode_token mocked to jwt_payload."""
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


async def make_user(db: AsyncSession, sub: str | None = None, full_name: str = "Test User") -> UserProfile:
    sub = sub or f"user-{uuid.uuid4()}"
    user = UserProfile(keycloak_sub=sub, email=f"{sub}@test.local", full_name=full_name)
    db.add(user)
    await db.flush()
    return user


async def grant_access(
    db: AsyncSession, user_id: uuid.UUID, quarry_id: uuid.UUID, level: int
) -> QuarryUserAccess:
    """Create a fresh Role at `level` and an active QuarryUserAccess for the user."""
    role = Role(name=f"role-{uuid.uuid4()}", level=level)
    db.add(role)
    await db.flush()
    access = QuarryUserAccess(user_id=user_id, quarry_id=quarry_id, role_id=role.id)
    db.add(access)
    await db.flush()
    return access


async def build_chain(
    db: AsyncSession,
    owner: UserProfile,
    *,
    with_model_version: bool = True,
    model_type: str = "mock",
    confidence_score: float = 0.87,
) -> dict:
    """Build a full Quarry -> ... -> Report -> Recommendation chain.

    `owner` is used for all created_by/captured_by FKs. Does NOT grant any
    quarry access — callers grant exactly the role they want to test.
    When with_model_version is False the AnalysisJob has no model_version
    (exercises the "mock" fallback path in build_report_read()).
    """
    now = datetime.now(tz=timezone.utc)

    quarry = Quarry(name=f"Quarry {uuid.uuid4()}", location_description="test")
    db.add(quarry)
    await db.flush()

    section = SiteSection(quarry_id=quarry.id, name="Block A", block_number="A-1")
    db.add(section)
    await db.flush()

    passport = BlastPassport(
        site_section_id=section.id,
        created_by_id=owner.id,
        explosive_type="ANFO",
        total_explosive_kg=2400.0,
        status=PassportStatus.ACTIVE,
    )
    db.add(passport)
    await db.flush()

    blast_event = BlastEvent(
        passport_id=passport.id,
        executed_by_id=owner.id,
        blast_datetime=now,
        actual_explosive_kg=2380.0,
    )
    db.add(blast_event)
    await db.flush()

    device = Device(serial_number=f"SN-{uuid.uuid4()}", model="ZED 2")
    db.add(device)
    await db.flush()

    calibration = Calibration(
        device_id=device.id,
        calibrated_by_id=owner.id,
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
    db.add(calibration)
    await db.flush()

    capture_session = CaptureSession(
        blast_event_id=blast_event.id,
        device_id=device.id,
        calibration_id=calibration.id,
        captured_by_id=owner.id,
        capture_datetime=now,
    )
    db.add(capture_session)
    await db.flush()

    model_version = None
    if with_model_version:
        model_version = ModelVersion(
            name="Pipeline",
            version_tag=f"{model_type}-v1",
            model_type=model_type,
            is_active=True,
        )
        db.add(model_version)
        await db.flush()

    job = AnalysisJob(
        capture_session_id=capture_session.id,
        model_version_id=model_version.id if model_version else None,
        status=JobStatus.COMPLETED,
        queued_at=now,
        started_at=now,
        completed_at=now,
    )
    db.add(job)
    await db.flush()

    result = AnalysisResult(
        job_id=job.id,
        p10_mm=120.5,
        p50_mm=345.2,
        p80_mm=580.8,
        rosin_rammler_n=1.42,
        rosin_rammler_xc=390.0,
        total_particles_counted=1847,
        confidence_score=confidence_score,
    )
    db.add(result)
    await db.flush()

    report = Report(
        analysis_result_id=result.id,
        generated_by_id=owner.id,
        report_type="granulometric",
        title="Test Report — Block A",
    )
    db.add(report)
    await db.flush()

    recommendation = Recommendation(
        report_id=report.id,
        generated_by_id=owner.id,
        recommendation_text="⚠ Mock pipeline — results are synthetic. Reference only.",
    )
    db.add(recommendation)
    await db.flush()

    return {
        "quarry": quarry,
        "section": section,
        "passport": passport,
        "blast_event": blast_event,
        "capture_session": capture_session,
        "model_version": model_version,
        "job": job,
        "result": result,
        "report": report,
        "recommendation": recommendation,
    }
