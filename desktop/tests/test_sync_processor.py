import httpx

from zmetrics_desktop.api.client import ApiClient
from zmetrics_desktop.config import Settings
from zmetrics_desktop.offline.sync_manager import MAX_ATTEMPTS, SyncManager
from zmetrics_desktop.offline.sync_processor import SyncProcessor


def _api(handler) -> ApiClient:
    return ApiClient(Settings(), transport=httpx.MockTransport(handler))


def _queue_with(*payloads: dict) -> SyncManager:
    queue = SyncManager(":memory:")
    for payload in payloads:
        queue.enqueue("post_json", payload)
    return queue


def test_offline_keeps_queue_untouched():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no network")

    queue = _queue_with({"path": "/quarries", "json": {"name": "K1"}})
    report = SyncProcessor(_api(handler), queue).process_once()

    assert report.online is False
    assert report.remaining == 1
    assert queue.pending()[0].attempts == 0  # offline must not count an attempt


def test_drains_queue_in_order_and_removes_sent():
    posted = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200)
        posted.append((request.url.path, request.read().decode()))
        return httpx.Response(201, json={"id": "x"})

    queue = _queue_with(
        {"path": "/quarries", "json": {"name": "K1"}},
        {"path": "/quarries", "json": {"name": "K2"}},
    )
    report = SyncProcessor(_api(handler), queue).process_once()

    assert (report.online, report.sent, report.failed, report.remaining) == (True, 2, 0, 0)
    assert queue.pending() == []
    assert [p[0] for p in posted] == ["/api/v1/quarries", "/api/v1/quarries"]
    assert "K1" in posted[0][1] and "K2" in posted[1][1]  # oldest first


def test_api_error_counts_attempt_and_continues():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200)
        if "bad" in request.read().decode():
            return httpx.Response(422, json={"detail": "invalid"})
        return httpx.Response(201)

    queue = _queue_with({"path": "/q", "json": {"name": "bad"}}, {"path": "/q", "json": {"name": "ok"}})
    report = SyncProcessor(_api(handler), queue).process_once()

    assert (report.sent, report.failed, report.remaining) == (1, 1, 1)
    leftover = queue.pending()[0]
    assert leftover.attempts == 1
    assert "422" in leftover.last_error


def test_transport_error_mid_drain_stops_without_counting_attempt():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200)
        calls["n"] += 1
        raise httpx.ConnectError("network dropped")

    queue = _queue_with({"path": "/q", "json": {}}, {"path": "/q", "json": {}})
    report = SyncProcessor(_api(handler), queue).process_once()

    assert calls["n"] == 1  # the pass stopped at the first connectivity failure
    assert (report.sent, report.failed, report.remaining) == (0, 0, 2)
    assert all(item.attempts == 0 for item in queue.pending())


def test_unknown_kind_is_marked_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    queue = SyncManager(":memory:")
    queue.enqueue("teleport", {"x": 1})
    report = SyncProcessor(_api(handler), queue).process_once()

    assert report.failed == 1
    assert "unknown kind" in queue.pending()[0].last_error


def test_exhausted_items_retire_to_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200)
        return httpx.Response(500, json={"detail": "boom"})

    queue = _queue_with({"path": "/q", "json": {}})
    processor = SyncProcessor(_api(handler), queue)
    for _ in range(MAX_ATTEMPTS):
        processor.process_once()

    assert queue.pending() == []  # no longer retried
    failed = queue.failed()
    assert len(failed) == 1 and failed[0].attempts == MAX_ATTEMPTS
