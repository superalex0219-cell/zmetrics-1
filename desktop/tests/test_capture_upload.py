"""Tests for the composite capture-upload operation and its sync-processor handler."""
from __future__ import annotations

import json

import httpx
import pytest

from zmetrics_desktop.api.client import ApiClient
from zmetrics_desktop.config import Settings
from zmetrics_desktop.offline.capture_upload import (
    KIND_CAPTURE_UPLOAD,
    build_payload,
    perform_capture_upload,
)
from zmetrics_desktop.offline.sync_manager import SyncManager
from zmetrics_desktop.offline.sync_processor import SyncProcessor

_SESSION = {
    "id": "cs1", "blast_event_id": "e1", "device_id": "d1", "calibration_id": "cal1",
    "captured_by_id": "u1", "capture_datetime": "2026-06-10T12:00:00Z", "frame_count": 0,
}
_JOB = {"id": "j1", "capture_session_id": "cs1", "status": "queued",
        "queued_at": "2026-06-10T12:00:01Z"}


def _handler_factory(calls: list[tuple[str, str]]):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        path = request.url.path
        if path.endswith("/capture-sessions"):
            return httpx.Response(201, json=_SESSION)
        if path.endswith("/artifacts"):
            return httpx.Response(201, json={
                "id": "a1", "capture_session_id": "cs1", "artifact_type": "left_frame",
                "storage_bucket": "zmetrics-frames", "storage_key": "k",
            })
        if path.endswith("/jobs"):
            return httpx.Response(201, json=_JOB)
        return httpx.Response(200, json={"status": "ok"})

    return handler


def _client(calls: list[tuple[str, str]]) -> ApiClient:
    return ApiClient(Settings(), transport=httpx.MockTransport(_handler_factory(calls)))


def _payload(tmp_path, stereo: bool) -> dict:
    left = tmp_path / "left.jpg"
    left.write_bytes(b"\xff\xd8left")
    right = None
    if stereo:
        right = tmp_path / "right.jpg"
        right.write_bytes(b"\xff\xd8right")
    return build_payload(
        quarry_id="q1", passport_id="p1", device_id="d1", calibration_id="cal1",
        left_path=str(left), right_path=str(right) if right else None,
    )


def test_stereo_upload_sends_session_two_frames_job(tmp_path):
    calls: list[tuple[str, str]] = []
    payload = _payload(tmp_path, stereo=True)

    session_id, job_id = perform_capture_upload(_client(calls), payload)

    assert (session_id, job_id) == ("cs1", "j1")
    assert [c[1].rsplit("/", 1)[-1] for c in calls] == [
        "capture-sessions", "artifacts", "artifacts", "jobs",
    ]
    assert not (tmp_path / "left.jpg").exists()  # cleaned up after success
    assert not (tmp_path / "right.jpg").exists()


def test_mono_upload_sends_left_frame_only(tmp_path):
    calls: list[tuple[str, str]] = []
    payload = _payload(tmp_path, stereo=False)

    perform_capture_upload(_client(calls), payload)

    artifact_posts = [c for c in calls if c[1].endswith("/artifacts")]
    assert len(artifact_posts) == 1


def test_failure_keeps_frame_files(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/capture-sessions"):
            return httpx.Response(201, json=_SESSION)
        return httpx.Response(500, json={"detail": "boom"})

    client = ApiClient(Settings(), transport=httpx.MockTransport(handler))
    payload = _payload(tmp_path, stereo=False)

    with pytest.raises(Exception):
        perform_capture_upload(client, payload)
    assert (tmp_path / "left.jpg").exists()  # ничего не удалено — будет ретрай


def test_queued_capture_drains_through_processor(tmp_path):
    calls: list[tuple[str, str]] = []
    queue = SyncManager(":memory:")
    queue.enqueue(KIND_CAPTURE_UPLOAD, _payload(tmp_path, stereo=False))

    report = SyncProcessor(_client(calls), queue).process_once()

    assert report.online and report.sent == 1 and report.remaining == 0
    assert any(c[1].endswith("/jobs") for c in calls)
    queue.close()


def test_handler_crash_counts_attempt_instead_of_wedging(tmp_path):
    """Missing frame file (handler bug) → mark_failure, очередь живёт дальше."""
    payload = _payload(tmp_path, stereo=False)
    (tmp_path / "left.jpg").unlink()  # симулируем потерю файла

    calls: list[tuple[str, str]] = []
    queue = SyncManager(":memory:")
    queue.enqueue(KIND_CAPTURE_UPLOAD, payload)

    report = SyncProcessor(_client(calls), queue).process_once()

    assert report.failed == 1
    item = queue.pending()[0]
    assert item.attempts == 1
    assert item.last_error
    queue.close()


def test_payload_is_json_serializable(tmp_path):
    payload = _payload(tmp_path, stereo=True)
    assert json.loads(json.dumps(payload)) == payload
