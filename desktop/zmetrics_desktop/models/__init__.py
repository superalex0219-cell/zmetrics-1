"""Pydantic DTOs mirroring the backend API contracts (``backend/app/schemas``).

These are plain data-transfer objects for the client — they must not import backend ORM
models.
"""
from zmetrics_desktop.models.dto import (
    AdminUser,
    AnalysisJob,
    AnalysisResult,
    Artifact,
    AuditLogEntry,
    BlastEvent,
    BlastPassport,
    Calibration,
    CaptureSession,
    CaptureSessionSummary,
    Device,
    FramePairSummary,
    Quarry,
    QuarryAccessEntry,
    Recommendation,
    Report,
    SiteSection,
    SizeBin,
    UserCreateResult,
    UserQuarryAccess,
)

__all__ = [
    "AdminUser",
    "AnalysisJob",
    "AnalysisResult",
    "Artifact",
    "AuditLogEntry",
    "BlastEvent",
    "BlastPassport",
    "Calibration",
    "CaptureSession",
    "CaptureSessionSummary",
    "Device",
    "FramePairSummary",
    "Quarry",
    "QuarryAccessEntry",
    "Recommendation",
    "Report",
    "SiteSection",
    "SizeBin",
    "UserCreateResult",
    "UserQuarryAccess",
]
