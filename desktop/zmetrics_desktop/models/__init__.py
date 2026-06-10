"""Pydantic DTOs mirroring the backend API contracts (``backend/app/schemas``).

These are plain data-transfer objects for the client — they must not import backend ORM
models.
"""
from zmetrics_desktop.models.dto import (
    AnalysisJob,
    AnalysisResult,
    Artifact,
    AuditLogEntry,
    BlastEvent,
    BlastPassport,
    Calibration,
    CaptureSession,
    Device,
    Quarry,
    QuarryAccessEntry,
    Recommendation,
    Report,
    SiteSection,
    SizeBin,
)

__all__ = [
    "AnalysisJob",
    "AnalysisResult",
    "Artifact",
    "AuditLogEntry",
    "BlastEvent",
    "BlastPassport",
    "Calibration",
    "CaptureSession",
    "Device",
    "Quarry",
    "QuarryAccessEntry",
    "Recommendation",
    "Report",
    "SiteSection",
    "SizeBin",
]
