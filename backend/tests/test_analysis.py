"""Tests: analysis job status and API schema validation."""

import uuid
from datetime import datetime, timezone

import pytest

from app.db.models.analysis import AnalysisJob, AnalysisResult, JobStatus


@pytest.mark.asyncio
async def test_analysis_job_defaults(db_session):
    job = AnalysisJob(
        capture_session_id=uuid.uuid4(),
        queued_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(job)
    await db_session.flush()

    assert job.status == JobStatus.QUEUED
    assert job.celery_task_id is None
    assert job.started_at is None
    assert job.completed_at is None
    assert job.error_message is None


@pytest.mark.asyncio
async def test_analysis_result_schema(db_session):
    job = AnalysisJob(
        capture_session_id=uuid.uuid4(),
        queued_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(job)
    await db_session.flush()

    result = AnalysisResult(
        job_id=job.id,
        p10_mm=85.5,
        p50_mm=245.0,
        p80_mm=410.3,
        rosin_rammler_n=1.2,
        rosin_rammler_xc=280.0,
        confidence_score=0.85,
        total_particles_counted=142,
        total_volume_m3=18.7,
    )
    db_session.add(result)
    await db_session.flush()

    assert result.p80_mm == pytest.approx(410.3, rel=1e-3)
    assert result.confidence_score == pytest.approx(0.85, rel=1e-3)
    assert result.job_id == job.id


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
