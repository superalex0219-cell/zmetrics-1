from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.capture import CaptureSession
    from app.db.models.passport import BlastPassport
    from app.db.models.user import UserProfile


class BlastEvent(Base, TimestampMixin):
    """The actual explosion event linked 0..1 to a BlastPassport."""

    __tablename__ = "blast_event"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # unique=True enforces the 0..1 relationship with passport
    passport_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blast_passport.id"), nullable=False, unique=True
    )
    executed_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profile.id"), nullable=False
    )
    blast_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_explosive_kg: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    weather_conditions: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    passport: Mapped[BlastPassport] = relationship("BlastPassport", back_populates="blast_event")
    executed_by: Mapped[UserProfile] = relationship("UserProfile", foreign_keys=[executed_by_id])
    capture_sessions: Mapped[list[CaptureSession]] = relationship(
        "CaptureSession", back_populates="blast_event"
    )


class Device(Base, TimestampMixin):
    """ZED 2 or other stereo camera device."""

    __tablename__ = "device"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    serial_number: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    # e.g., "ZED 2", "ZED X"
    firmware_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    calibrations: Mapped[list[Calibration]] = relationship(
        "Calibration", back_populates="device"
    )
    capture_sessions: Mapped[list[CaptureSession]] = relationship(
        "CaptureSession", back_populates="device"
    )


class Calibration(Base, TimestampMixin):
    """Stereo camera calibration parameters. Stored as JSONB for camera model flexibility."""

    __tablename__ = "calibration"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("device.id"), nullable=False, index=True
    )
    calibrated_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profile.id"), nullable=False
    )

    # Camera intrinsic/extrinsic parameters stored as JSONB dicts
    # Structure: {"fx": float, "fy": float, "cx": float, "cy": float}
    left_camera_matrix: Mapped[dict] = mapped_column(JSONB, nullable=False)
    right_camera_matrix: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Distortion coefficients: {"k1": float, "k2": float, "p1": float, "p2": float, "k3": float}
    left_dist_coeffs: Mapped[dict] = mapped_column(JSONB, nullable=False)
    right_dist_coeffs: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Stereo extrinsics
    rotation_matrix: Mapped[dict] = mapped_column(JSONB, nullable=False)
    translation_vector: Mapped[dict] = mapped_column(JSONB, nullable=False)
    baseline_mm: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    image_width_px: Mapped[int] = mapped_column(Integer, nullable=False)
    image_height_px: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    device: Mapped[Device] = relationship("Device", back_populates="calibrations")
    calibrated_by: Mapped[UserProfile] = relationship(
        "UserProfile", foreign_keys=[calibrated_by_id]
    )
    capture_sessions: Mapped[list[CaptureSession]] = relationship(
        "CaptureSession", back_populates="calibration"
    )
