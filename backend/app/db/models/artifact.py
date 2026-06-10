from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.capture import CaptureSession


class ArtifactType(str, enum.Enum):
    LEFT_FRAME = "left_frame"
    RIGHT_FRAME = "right_frame"
    DEPTH_MAP = "depth_map"
    POINT_CLOUD = "point_cloud"
    MASK = "mask"
    PARTICLE_LIST = "particle_list"
    REPORT_FILE = "report_file"


class Artifact(Base, TimestampMixin):
    """A file artifact stored in MinIO. Can be a raw frame or a derived pipeline output."""

    __tablename__ = "artifact"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    capture_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("capture_session.id"), nullable=False, index=True
    )
    # Optional: link to the analysis job that produced this artifact
    analysis_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_job.id"), nullable=True, index=True
    )

    artifact_type: Mapped[ArtifactType] = mapped_column(
        SAEnum(ArtifactType, name="artifact_type"), nullable=False
    )
    storage_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    # e.g., "sessions/{capture_session_id}/frames/left_0001.jpg"
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)

    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # For multi-frame captures: 0-indexed frame position
    frame_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Extra metadata (image dimensions, etc.)
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    capture_session: Mapped[CaptureSession] = relationship(
        "CaptureSession",
        back_populates="artifacts",
        foreign_keys=[capture_session_id],
    )
