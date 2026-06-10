from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.analysis import JobStatus


class AnalysisJobCreate(BaseModel):
    # capture_session_id comes from the URL path, not the body.
    model_version_id: UUID | None = None
    # Which frame pair of the session to analyze (series capture, CAP-MULTI).
    frame_index: int = Field(default=0, ge=0)


class AnalysisJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    capture_session_id: UUID
    model_version_id: UUID | None
    frame_index: int
    celery_task_id: str | None
    status: JobStatus
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    pipeline_log: dict | None


class AnalysisResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    p10_mm: float | None
    p50_mm: float | None
    p80_mm: float | None
    rosin_rammler_n: float | None
    rosin_rammler_xc: float | None
    uniformity_index: float | None
    oversize_percent: float | None
    fines_percent: float | None
    total_particles_counted: int | None
    total_volume_m3: float | None
    confidence_score: float | None
    confidence_notes: str | None
    size_distribution: list | None
    created_at: datetime
