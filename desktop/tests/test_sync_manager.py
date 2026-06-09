from zmetrics_desktop.offline.sync_manager import MAX_ATTEMPTS, SyncManager


def test_enqueue_and_pending():
    mgr = SyncManager(":memory:")
    key = mgr.enqueue("upload_frames", {"capture_session_id": "abc", "eye": "left"})

    pending = mgr.pending()
    assert len(pending) == 1
    item = pending[0]
    assert item.idempotency_key == key
    assert item.kind == "upload_frames"
    assert item.payload["capture_session_id"] == "abc"
    assert item.attempts == 0


def test_remove_on_success():
    mgr = SyncManager(":memory:")
    key = mgr.enqueue("create_passport", {"x": 1})
    mgr.remove(key)
    assert mgr.pending() == []


def test_failures_move_item_to_failed_after_max_attempts():
    mgr = SyncManager(":memory:")
    key = mgr.enqueue("upload_frames", {"x": 1})
    for _ in range(MAX_ATTEMPTS):
        mgr.mark_failure(key, "network down")

    assert mgr.pending() == []
    failed = mgr.failed()
    assert len(failed) == 1
    assert failed[0].attempts == MAX_ATTEMPTS
    assert failed[0].last_error == "network down"


def test_persists_to_file(tmp_path):
    db = tmp_path / "queue.db"
    mgr = SyncManager(db)
    key = mgr.enqueue("create_passport", {"name": "p1"})
    mgr.close()

    reopened = SyncManager(db)
    pending = reopened.pending()
    assert len(pending) == 1
    assert pending[0].idempotency_key == key
