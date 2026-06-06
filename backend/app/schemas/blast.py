from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.models.artifact import ArtifactType


class DeviceCreate(BaseModel):
    serial_number: str
    model: str
    firmware_version: str | None = None
    notes: str | None = None


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    serial_number: str
    model: str
    firmware_version: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CalibrationCreate(BaseModel):
    left_camera_matrix: dict
    right_camera_matrix: dict
    left_dist_coeffs: dict
    right_dist_coeffs: dict
    rotation_matrix: dict
    translation_vector: dict
    baseline_mm: float
    image_width_px: int
    image_height_px: int


class CalibrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_id: UUID
    calibrated_by_id: UUID
    left_camera_matrix: dict
    right_camera_matrix: dict
    left_dist_coeffs: dict
    right_dist_coeffs: dict
    rotation_matrix: dict
    translation_vector: dict
    baseline_mm: float
    image_width_px: int
    image_height_px: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BlastEventCreate(BaseModel):
    blast_datetime: datetime
    actual_explosive_kg: float | None = None
    weather_conditions: str | None = None
    notes: str | None = None


class BlastEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    passport_id: UUID
    executed_by_id: UUID
    blast_datetime: datetime
    actual_explosive_kg: float | None
    weather_conditions: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CaptureSessionCreate(BaseModel):
    device_id: UUID
    calibration_id: UUID
    capture_datetime: datetime | None = None  # defaults to now() server-side if omitted
    notes: str | None = None


class CaptureSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    blast_event_id: UUID
    device_id: UUID
    calibration_id: UUID
    captured_by_id: UUID
    capture_datetime: datetime
    frame_count: int
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    capture_session_id: UUID
    artifact_type: ArtifactType
    storage_bucket: str
    storage_key: str
    file_size_bytes: int | None
    content_type: str | None
    checksum_sha256: str | None
    frame_index: int | None
    created_at: datetime
    updated_at: datetime


class ArtifactUrlRead(BaseModel):
    url: str
    expires_in: int
