"""DTOs for the ``/api/v1`` contract — field-for-field with the backend Pydantic schemas
(see the former ``frontend/src/types.ts`` for the reference shape).

``extra="ignore"``: the backend may add fields without breaking older clients.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _Dto(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Quarry(_Dto):
    id: str
    name: str
    location_description: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class SiteSection(_Dto):
    id: str
    quarry_id: str
    name: str
    block_number: str | None = None
    description: str | None = None


class BlastPassport(_Dto):
    id: str
    site_section_id: str
    status: str  # draft | submitted | approved | active | completed | superseded
    revision_number: int
    blast_date_planned: str | None = None
    explosive_type: str | None = None
    total_explosive_kg: float | None = None
    number_of_holes: int | None = None
    hole_diameter_mm: float | None = None
    hole_depth_m: float | None = None
    burden_m: float | None = None
    spacing_m: float | None = None
    stemming_m: float | None = None
    target_p80_mm: float | None = None
    notes: str | None = None
    created_at: str
    updated_at: str


class BlastEvent(_Dto):
    id: str
    passport_id: str
    executed_by_id: str
    blast_datetime: str
    actual_explosive_kg: float | None = None
    weather_conditions: str | None = None
    notes: str | None = None
    created_at: str


class SizeBin(_Dto):
    size_mm: float
    cumulative_passing_pct: float


class AnalysisResult(_Dto):
    id: str
    p10_mm: float | None = None
    p50_mm: float | None = None
    p80_mm: float | None = None
    rosin_rammler_n: float | None = None
    rosin_rammler_xc: float | None = None
    oversize_percent: float | None = None
    fines_percent: float | None = None
    confidence_score: float | None = None
    confidence_notes: str | None = None
    size_distribution: list[SizeBin] | None = None


class Report(_Dto):
    id: str
    title: str
    report_type: str
    analysis_method: str  # "mock" | "real"
    analysis_result_id: str
    confidence_score: float | None = None
    model_version_tag: str | None = None
    created_at: str


class Recommendation(_Dto):
    id: str
    report_id: str
    status: str  # requires_human_review | reviewed | accepted | rejected
    recommendation_text: str
    # Reference values only — displayed read-only, NEVER written back to a passport.
    parameter_suggestions: dict | None = None
    reviewed_at: str | None = None
    reviewer_notes: str | None = None
    created_at: str


class Device(_Dto):
    id: str
    serial_number: str
    model: str
    firmware_version: str | None = None
    notes: str | None = None


class Calibration(_Dto):
    id: str
    device_id: str
    baseline_mm: float
    image_width_px: int
    image_height_px: int
    is_active: bool
    created_at: str


class CaptureSession(_Dto):
    id: str
    blast_event_id: str
    device_id: str
    calibration_id: str
    captured_by_id: str
    capture_datetime: str
    frame_count: int
    notes: str | None = None


class AnalysisJob(_Dto):
    id: str
    capture_session_id: str
    model_version_id: str | None = None
    frame_index: int = 0
    status: str  # queued | running | completed | failed
    queued_at: str
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None
    pipeline_log: dict | None = None


class Artifact(_Dto):
    id: str
    capture_session_id: str
    artifact_type: str
    storage_bucket: str
    storage_key: str
    file_size_bytes: int | None = None
    content_type: str | None = None
    frame_index: int | None = None


class FramePairSummary(_Dto):
    """One frame pair of a capture session + its latest job status."""

    frame_index: int
    has_left: bool
    has_right: bool
    job_id: str | None = None
    job_status: str | None = None  # queued | running | completed | failed


class CaptureSessionSummary(_Dto):
    """Blast photo list row: session with per-frame aggregates (CAP-MULTI)."""

    id: str
    capture_datetime: str
    captured_by_id: str
    captured_by_name: str | None = None
    device_id: str
    calibration_id: str
    frame_count: int
    notes: str | None = None
    frames: list[FramePairSummary] = []
    jobs_total: int = 0
    jobs_completed: int = 0
    jobs_failed: int = 0


class QuarryAccessEntry(_Dto):
    """Caller's effective role on one quarry (``GET /api/v1/access``). Used only for
    UI gating — the backend enforces roles on every endpoint regardless."""

    quarry_id: str
    quarry_name: str
    role_name: str  # user | surveyor | blaster | admin
    role_level: int  # 1..4


class AdminUser(_Dto):
    id: str
    email: str
    full_name: str
    is_active: bool
    created_at: str


class UserCreateResult(_Dto):
    user: AdminUser
    # Показывается РОВНО один раз; не хранить, не логировать, очищать из state.
    temporary_password: str


class UserQuarryAccess(_Dto):
    access_id: str
    quarry_id: str
    quarry_name: str
    role_name: str
    role_level: int


class AuditLogEntry(_Dto):
    id: str
    actor_id: str | None = None
    entity_type: str
    entity_id: str
    action: str
    occurred_at: str
    old_value: dict | None = None
    new_value: dict | None = None
