from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.capture import CaptureSession
    from app.db.models.report import Report


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ModelVersion(Base, TimestampMixin):
    """ML model registry entry."""

    __tablename__ = "model_version"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # e.g., "yolov8-seg-quarry-v1", "sam-quarry-v1", "mock-v1"
    version_tag: Mapped[str] = mapped_column(String(100), nullable=False)
    model_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g., "yolo_seg", "sam", "mock"
    artifact_storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=False)
    # {"mAP50": 0.83, "dataset": "quarry-internal-v2"}
    metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AnalysisJob(Base, TimestampMixin):
    """Celery analysis job record. One job per capture session (can retry)."""

    __tablename__ = "analysis_job"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    capture_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("capture_session.id"), nullable=False, index=True
    )
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_version.id"), nullable=True, index=True
    )

    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="job_status"),
        nullable=False,
        default=JobStatus.QUEUED,
    )

    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # {"steps": [{"name": "calibration_load", "status": "ok", "duration_s": 0.1}, ...]}
    pipeline_log: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    capture_session: Mapped[CaptureSession] = relationship(
        "CaptureSession", back_populates="analysis_jobs"
    )
    model_version: Mapped[ModelVersion | None] = relationship("ModelVersion")
    result: Mapped[AnalysisResult | None] = relationship(
        "AnalysisResult", back_populates="job", uselist=False
    )


class AnalysisResult(Base, TimestampMixin):
    """Computed granulometric distribution results from a completed AnalysisJob."""

    __tablename__ = "analysis_result"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Unique: one result per job
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_job.id"), nullable=False, unique=True
    )

    # Granulometric distribution (millimeters)
    p10_mm: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    p50_mm: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    p80_mm: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)

    # Rosin-Rammler fit: R(x) = exp(-(x/xc)^n)
    rosin_rammler_n: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    rosin_rammler_xc: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)

    # Derived metrics
    uniformity_index: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    oversize_percent: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    fines_percent: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    total_particles_counted: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_volume_m3: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)

    # Confidence (0.0–1.0)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    confidence_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Raw distribution: [{"size_mm": float, "cumulative_passing_pct": float}, ...]
    size_distribution: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    job: Mapped[AnalysisJob] = relationship("AnalysisJob", back_populates="result")
    report: Mapped[Report | None] = relationship("Report", back_populates="analysis_result", uselist=False)
