"""Composite capture-upload operation: session → frames → analysis job.

Used twice:
- online — the capture screen runs :func:`perform_capture_upload` directly (and then
  polls the returned job);
- offline — the screen saves the JPEG frames to disk, enqueues a ``capture_upload``
  item, and the sync processor replays it via :func:`handle_capture_upload` when the
  backend is reachable again.

The payload carries only JSON-serializable data; frame bytes live as files under the
offline frames directory and are deleted after a confirmed upload.
"""
from __future__ import annotations

from pathlib import Path

from zmetrics_desktop.api.client import ApiClient
from zmetrics_desktop.api.zmetrics import ZMetricsApi
from zmetrics_desktop.offline.sync_manager import PendingUpload

KIND_CAPTURE_UPLOAD = "capture_upload"


def build_payload(
    *,
    quarry_id: str,
    passport_id: str,
    device_id: str,
    calibration_id: str,
    left_path: str,
    right_path: str | None,
) -> dict:
    return {
        "quarry_id": quarry_id,
        "passport_id": passport_id,
        "device_id": device_id,
        "calibration_id": calibration_id,
        "left_path": left_path,
        "right_path": right_path,
    }


def perform_capture_upload(client: ApiClient, payload: dict) -> tuple[str, str]:
    """Create the capture session, upload the frame(s), enqueue the analysis job.

    Returns ``(session_id, job_id)``. Frame files are deleted only after the job is
    queued server-side, so a mid-way failure keeps them for the retry. На повторе
    возможен дубль сессии (бэкенд пока без Idempotency-Key — см. roadmap).
    """
    api = ZMetricsApi(client)
    session = api.create_capture_session(
        payload["quarry_id"],
        payload["passport_id"],
        payload["device_id"],
        payload["calibration_id"],
    )

    left_path = Path(payload["left_path"])
    api.upload_artifact(session.id, left_path.read_bytes(), "left_frame", 0)
    right_path = Path(payload["right_path"]) if payload.get("right_path") else None
    if right_path is not None:
        api.upload_artifact(session.id, right_path.read_bytes(), "right_frame", 0)

    job = api.enqueue_job(session.id)

    left_path.unlink(missing_ok=True)
    if right_path is not None:
        right_path.unlink(missing_ok=True)
    return session.id, job.id


def handle_capture_upload(client: ApiClient, item: PendingUpload) -> None:
    """Sync-processor handler for queued captures."""
    perform_capture_upload(client, item.payload)
