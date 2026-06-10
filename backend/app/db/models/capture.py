from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.analysis import AnalysisJob
    from app.db.models.artifact import Artifact
    from app.db.models.blast import BlastEvent, Calibration, Device
    from app.db.models.user import UserProfile


class CaptureSession(Base, TimestampMixin):
    """A stereo image capture session after a blast event."""

    __tablename__ = "capture_session"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    blast_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blast_event.id"), nullable=False, index=True
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("device.id"), nullable=False
    )
    calibration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calibration.id"), nullable=False
    )
    captured_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profile.id"), nullable=False
    )
    capture_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    frame_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    blast_event: Mapped[BlastEvent] = relationship(
        "BlastEvent", back_populates="capture_sessions"
    )
    device: Mapped[Device] = relationship("Device", back_populates="capture_sessions")
    calibration: Mapped[Calibration] = relationship(
        "Calibration", back_populates="capture_sessions"
    )
    captured_by: Mapped[UserProfile] = relationship(
        "UserProfile", foreign_keys=[captured_by_id]
    )
    artifacts: Mapped[list[Artifact]] = relationship(
        "Artifact", back_populates="capture_session", foreign_keys="Artifact.capture_session_id"
    )
    analysis_jobs: Mapped[list[AnalysisJob]] = relationship(
        "AnalysisJob", back_populates="capture_session"
    )
