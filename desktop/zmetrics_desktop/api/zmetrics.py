"""Typed facade over ``ApiClient`` — one method per backend endpoint.

Mirrors the former ``frontend/src/api.ts`` route-for-route so screen ports can be checked
against it. Paginated endpoints return plain lists (page 1), like the old client did.

SAFETY: passport state transitions (submit/approve/activate/complete) and recommendation
reviews exist here ONLY as explicit user actions — never call them automatically.
"""
from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from zmetrics_desktop.api.client import ApiClient
from zmetrics_desktop.models import (
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
    Quarry,
    QuarryAccessEntry,
    Recommendation,
    Report,
    SiteSection,
    UserCreateResult,
    UserQuarryAccess,
)

T = TypeVar("T", bound=BaseModel)


def _items(payload: dict, model: type[T]) -> list[T]:
    """Unwrap a paginated response ``{"items": [...], "total": n, ...}``."""
    return [model.model_validate(item) for item in payload["items"]]


class ZMetricsApi:
    def __init__(self, client: ApiClient) -> None:
        self._client = client

    # --- Access -----------------------------------------------------------------------

    def get_my_access(self) -> list[QuarryAccessEntry]:
        """Caller's role per quarry — UI gating only; the backend re-checks every call."""
        return [
            QuarryAccessEntry.model_validate(item)
            for item in self._client.get("/me/access")
        ]

    # --- Quarries / sections ----------------------------------------------------------

    def list_quarries(self) -> list[Quarry]:
        return _items(self._client.get("/quarries"), Quarry)

    def create_quarry(self, body: dict) -> Quarry:
        return Quarry.model_validate(self._client.post("/quarries", json=body))

    def update_quarry(self, quarry_id: str, body: dict) -> Quarry:
        """EDIT-1: частичное редактирование; сервер пишет AuditLog."""
        return Quarry.model_validate(self._client.patch(f"/quarries/{quarry_id}", json=body))

    def list_sections(self, quarry_id: str) -> list[SiteSection]:
        return _items(self._client.get(f"/quarries/{quarry_id}/sections"), SiteSection)

    def create_section(self, quarry_id: str, body: dict) -> SiteSection:
        return SiteSection.model_validate(
            self._client.post(f"/quarries/{quarry_id}/sections", json=body)
        )

    def update_section(self, quarry_id: str, section_id: str, body: dict) -> SiteSection:
        """EDIT-1: частичное редактирование; сервер пишет AuditLog."""
        return SiteSection.model_validate(
            self._client.patch(f"/quarries/{quarry_id}/sections/{section_id}", json=body)
        )

    # --- Blast passports --------------------------------------------------------------

    def list_passports(self, quarry_id: str) -> list[BlastPassport]:
        return _items(self._client.get(f"/quarries/{quarry_id}/passports"), BlastPassport)

    def get_passport(self, quarry_id: str, passport_id: str) -> BlastPassport:
        return BlastPassport.model_validate(
            self._client.get(f"/quarries/{quarry_id}/passports/{passport_id}")
        )

    def create_passport(self, quarry_id: str, body: dict) -> BlastPassport:
        return BlastPassport.model_validate(
            self._client.post(f"/quarries/{quarry_id}/passports", json=body)
        )

    def update_passport(self, quarry_id: str, passport_id: str, body: dict) -> BlastPassport:
        """EDIT-1: правка только DRAFT-паспорта (сервер вернёт 409 для остальных)."""
        return BlastPassport.model_validate(
            self._client.patch(f"/quarries/{quarry_id}/passports/{passport_id}", json=body)
        )

    def transition_passport(self, quarry_id: str, passport_id: str, action: str) -> BlastPassport:
        """Explicit human-initiated state transition.

        ``action``: submit | approve | activate | complete. SAFETY: only call from a
        button handler — никогда автоматически.
        """
        assert action in ("submit", "approve", "activate", "complete")
        return BlastPassport.model_validate(
            self._client.post(f"/quarries/{quarry_id}/passports/{passport_id}/{action}", json={})
        )

    # --- Blast events -------------------------------------------------------------------

    def get_blast_event(self, quarry_id: str, passport_id: str) -> BlastEvent:
        return BlastEvent.model_validate(
            self._client.get(f"/quarries/{quarry_id}/passports/{passport_id}/blast-event")
        )

    def create_blast_event(self, quarry_id: str, passport_id: str, body: dict) -> BlastEvent:
        return BlastEvent.model_validate(
            self._client.post(
                f"/quarries/{quarry_id}/passports/{passport_id}/blast-event", json=body
            )
        )

    def update_blast_event(self, quarry_id: str, passport_id: str, body: dict) -> BlastEvent:
        """EDIT-1: корректировка факта взрыва; сервер пишет AuditLog."""
        return BlastEvent.model_validate(
            self._client.patch(
                f"/quarries/{quarry_id}/passports/{passport_id}/blast-event", json=body
            )
        )

    # --- Reports / recommendations / results --------------------------------------------

    def list_reports(self, quarry_id: str) -> list[Report]:
        return _items(self._client.get(f"/quarries/{quarry_id}/reports"), Report)

    def export_report(self, report_id: str) -> dict:
        return self._client.get(f"/reports/{report_id}/export")

    def list_recommendations(self, report_id: str) -> list[Recommendation]:
        return _items(
            self._client.get(f"/reports/{report_id}/recommendations"), Recommendation
        )

    def review_recommendation(
        self, report_id: str, rec_id: str, status: str, notes: str | None = None
    ) -> Recommendation:
        """Explicit human review action (accept/reject/reviewed) — never automatic."""
        return Recommendation.model_validate(
            self._client.post(
                f"/reports/{report_id}/recommendations/{rec_id}/review",
                json={"status": status, "reviewer_notes": notes},
            )
        )

    def get_analysis_result(self, result_id: str) -> AnalysisResult:
        return AnalysisResult.model_validate(
            self._client.get(f"/analysis-results/{result_id}")
        )

    # --- Devices / calibrations ----------------------------------------------------------

    def list_devices(self) -> list[Device]:
        return _items(self._client.get("/devices"), Device)

    def create_device(self, body: dict) -> Device:
        return Device.model_validate(self._client.post("/devices", json=body))

    def update_device(self, device_id: str, body: dict) -> Device:
        """EDIT-1: model/firmware/notes; серийник не меняется."""
        return Device.model_validate(self._client.patch(f"/devices/{device_id}", json=body))

    def update_calibration(self, device_id: str, calibration_id: str, body: dict) -> Calibration:
        """EDIT-1: только is_active; матрицы фиксированы (новая калибровка = новая запись)."""
        return Calibration.model_validate(
            self._client.patch(
                f"/devices/{device_id}/calibrations/{calibration_id}", json=body
            )
        )

    def list_calibrations(self, device_id: str) -> list[Calibration]:
        return _items(self._client.get(f"/devices/{device_id}/calibrations"), Calibration)

    def add_calibration(self, device_id: str, body: dict) -> Calibration:
        return Calibration.model_validate(
            self._client.post(f"/devices/{device_id}/calibrations", json=body)
        )

    # --- Capture flow ---------------------------------------------------------------------

    def create_capture_session(
        self, quarry_id: str, passport_id: str, device_id: str, calibration_id: str
    ) -> CaptureSession:
        return CaptureSession.model_validate(
            self._client.post(
                f"/quarries/{quarry_id}/passports/{passport_id}/blast-event/capture-sessions",
                json={"device_id": device_id, "calibration_id": calibration_id},
            )
        )

    def upload_artifact(
        self,
        session_id: str,
        content: bytes,
        artifact_type: str,  # left_frame | right_frame
        frame_index: int,
        filename: str = "frame.jpg",
    ) -> Artifact:
        return Artifact.model_validate(
            self._client.post_multipart(
                f"/capture-sessions/{session_id}/artifacts",
                data={"artifact_type": artifact_type, "frame_index": str(frame_index)},
                files={"file": (filename, content, "image/jpeg")},
            )
        )

    def enqueue_job(self, session_id: str, frame_index: int = 0) -> AnalysisJob:
        return AnalysisJob.model_validate(
            self._client.post(
                f"/captures/{session_id}/jobs", json={"frame_index": frame_index}
            )
        )

    def list_jobs(self, session_id: str) -> list[AnalysisJob]:
        return _items(self._client.get(f"/captures/{session_id}/jobs"), AnalysisJob)

    def get_capture_summary(
        self, quarry_id: str, passport_id: str
    ) -> list[CaptureSessionSummary]:
        """Photo list of a blast: sessions + per-frame upload/job status."""
        return [
            CaptureSessionSummary.model_validate(item)
            for item in self._client.get(
                f"/quarries/{quarry_id}/passports/{passport_id}/blast-event/capture-summary"
            )
        ]

    def get_job(self, session_id: str, job_id: str) -> AnalysisJob:
        return AnalysisJob.model_validate(
            self._client.get(f"/captures/{session_id}/jobs/{job_id}")
        )

    def get_job_result(self, session_id: str, job_id: str) -> AnalysisResult:
        return AnalysisResult.model_validate(
            self._client.get(f"/captures/{session_id}/jobs/{job_id}/result")
        )

    # --- Admin: user management (ADMIN-USERS) ------------------------------------------------

    def admin_list_users(self) -> list[AdminUser]:
        return _items(self._client.get("/admin/users", params={"page_size": 200}), AdminUser)

    def admin_create_user(self, email: str, full_name: str) -> UserCreateResult:
        """Возвращает временный пароль РОВНО один раз — не хранить и не логировать."""
        return UserCreateResult.model_validate(
            self._client.post("/admin/users", json={"email": email, "full_name": full_name})
        )

    def admin_update_user(self, user_id: str, body: dict) -> AdminUser:
        return AdminUser.model_validate(self._client.patch(f"/admin/users/{user_id}", json=body))

    def admin_deactivate_user(self, user_id: str) -> None:
        self._client.delete(f"/admin/users/{user_id}")

    def admin_reset_password(self, user_id: str) -> str:
        """Возвращает новый временный пароль РОВНО один раз."""
        payload = self._client.post(f"/admin/users/{user_id}/reset-password", json={})
        return payload["temporary_password"]

    def admin_user_access(self, user_id: str) -> list[UserQuarryAccess]:
        return [
            UserQuarryAccess.model_validate(item)
            for item in self._client.get(f"/admin/users/{user_id}/access")
        ]

    def admin_grant_access(self, quarry_id: str, user_id: str, role_name: str) -> dict:
        return self._client.post(
            f"/admin/quarries/{quarry_id}/access",
            json={"user_id": user_id, "quarry_id": quarry_id, "role_name": role_name},
        )

    def admin_revoke_access(self, quarry_id: str, access_id: str) -> None:
        self._client.delete(f"/admin/quarries/{quarry_id}/access/{access_id}")

    # --- Admin: audit ---------------------------------------------------------------------------

    def passport_audit_log(self, passport_id: str) -> list[AuditLogEntry]:
        """Admin-only; callers must treat a 403 as an empty list."""
        payload = self._client.get(
            "/admin/audit-logs",
            params={
                "entity_type": "blast_passport",
                "entity_id": passport_id,
                "page_size": 200,
            },
        )
        return [AuditLogEntry.model_validate(item) for item in payload]
