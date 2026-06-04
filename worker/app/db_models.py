"""
Minimal SQLAlchemy models for the worker.
Must stay in sync with backend/app/db/models/analysis.py and report.py.
Only the tables the worker reads/writes are defined here.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisJob(Base):
    __tablename__ = "analysis_job"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    capture_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="job_status", create_type=False),
        nullable=False,
        default=JobStatus.QUEUED,
    )
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    pipeline_log: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AnalysisResult(Base):
    __tablename__ = "analysis_result"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("analysis_job.id"), nullable=False, unique=True)
    p10_mm: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    p50_mm: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    p80_mm: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    rosin_rammler_n: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    rosin_rammler_xc: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    uniformity_index: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    oversize_percent: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    fines_percent: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    total_particles_counted: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_volume_m3: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    confidence_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_distribution: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
