"""Composite capture-upload operation: session → frame series → analysis jobs.

Used twice:
- online — the capture screen runs :func:`perform_capture_upload` directly (and then
  polls the returned jobs);
- offline — the screen saves the JPEG frames to disk, enqueues a ``capture_upload``
  item, and the sync processor replays it via :func:`handle_capture_upload` when the
  backend is reachable again.

CAP-MULTI: one session holds a series of frame pairs (``frame_index`` 0..N-1); each
pair gets its own analysis job. The payload carries only JSON-serializable data; frame
bytes live as files under the offline frames directory and are deleted after a
confirmed upload. Legacy single-pair payloads (``left_path``/``right_path`` at the top
level) are still replayed correctly.
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
    """Single-pair payload (kept for the one-shot capture path)."""
    return build_series_payload(
        quarry_id=quarry_id,
        passport_id=passport_id,
        device_id=device_id,
        calibration_id=calibration_id,
        frames=[{"left_path": left_path, "right_path": right_path}],
    )


def build_series_payload(
    *,
    quarry_id: str,
    passport_id: str,
    device_id: str,
    calibration_id: str,
    frames: list[dict],
) -> dict:
    """Series payload: ``frames`` is ``[{"left_path": str, "right_path": str|None}]``."""
    return {
        "quarry_id": quarry_id,
        "passport_id": passport_id,
        "device_id": device_id,
        "calibration_id": calibration_id,
        "frames": frames,
    }


def _normalize_frames(payload: dict) -> list[dict]:
    """Either the new ``frames`` list or a legacy flat single-pair payload."""
    if "frames" in payload:
        return payload["frames"]
    return [{
        "left_path": payload["left_path"],
        "right_path": payload.get("right_path"),
    }]


def perform_capture_upload(client: ApiClient, payload: dict) -> tuple[str, list[str]]:
    """Create the capture session, upload all frame pairs, enqueue one job per pair.

    Returns ``(session_id, [job_id, ...])`` — job order matches frame_index order.
    Frame files are deleted only after all jobs are queued server-side, so a mid-way
    failure keeps them for the retry. На повторе возможен дубль сессии (бэкенд пока
    без Idempotency-Key — см. roadmap).
    """
    api = ZMetricsApi(client)
    frames = _normalize_frames(payload)
    session = api.create_capture_session(
        payload["quarry_id"],
        payload["passport_id"],
        payload["device_id"],
        payload["calibration_id"],
    )

    for index, frame in enumerate(frames):
        left_path = Path(frame["left_path"])
        api.upload_artifact(session.id, left_path.read_bytes(), "left_frame", index)
        if frame.get("right_path"):
            right_path = Path(frame["right_path"])
            api.upload_artifact(session.id, right_path.read_bytes(), "right_frame", index)

    job_ids = [api.enqueue_job(session.id, frame_index=i).id for i in range(len(frames))]

    for frame in frames:
        Path(frame["left_path"]).unlink(missing_ok=True)
        if frame.get("right_path"):
            Path(frame["right_path"]).unlink(missing_ok=True)
    return session.id, job_ids


def handle_capture_upload(client: ApiClient, item: PendingUpload) -> None:
    """Sync-processor handler for queued captures."""
    perform_capture_upload(client, item.payload)
