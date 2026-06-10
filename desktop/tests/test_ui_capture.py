"""Offscreen tests for the capture screen: gating, passport filter, offline outcome."""
from __future__ import annotations

import os
from types import SimpleNamespace

import httpx
import numpy as np
import pytest

from zmetrics_desktop.api.client import ApiClient
from zmetrics_desktop.capture.stereo import StereoFrame
from zmetrics_desktop.config import Settings
from zmetrics_desktop.models import BlastPassport, Quarry, QuarryAccessEntry

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from zmetrics_desktop.ui.capture import CaptureScreen  # noqa: E402
from zmetrics_desktop.ui.state import AppState  # noqa: E402

_Q1 = Quarry(id="q1", name="Карьер 1")


def _passport(pid: str, status: str) -> BlastPassport:
    return BlastPassport(
        id=pid, site_section_id="s1", status=status, revision_number=1,
        created_at="2026-06-10", updated_at="2026-06-10",
    )


def _frame() -> StereoFrame:
    image = np.zeros((4, 4, 3), dtype=np.uint8)
    return StereoFrame(left=image, right=None, width=4, height=4, side_by_side=False)


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    return app or QApplication([])


@pytest.fixture(autouse=True)
def sync_submit(monkeypatch):
    def run_inline(fn, on_success=None, on_error=None):
        try:
            result = fn()
        except Exception as exc:
            if on_error is not None:
                on_error(str(exc))
        else:
            if on_success is not None:
                on_success(result)

    monkeypatch.setattr("zmetrics_desktop.ui.capture.submit", run_inline)


def _context(tmp_path) -> SimpleNamespace:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": [], "total": 0, "page": 1, "page_size": 50})

    settings = Settings(offline_db_path=tmp_path / "offline.db")
    from zmetrics_desktop.offline.sync_manager import SyncManager

    return SimpleNamespace(
        api=ApiClient(settings, transport=httpx.MockTransport(handler)),
        settings=settings,
        make_sync_manager=lambda: SyncManager(settings.offline_db_path),
    )


def test_capture_disabled_without_role_or_frame(qapp, tmp_path):
    state = AppState()
    state.set_quarry(_Q1)
    screen = CaptureScreen(_context(tmp_path), state)
    assert not screen._capture_button.isEnabled()  # роли нет и кадра нет

    state.set_access([QuarryAccessEntry(
        quarry_id="q1", quarry_name="Карьер 1", role_name="surveyor", role_level=2,
    )])
    assert not screen._capture_button.isEnabled()  # роль есть, кадра нет

    screen._on_preview_frame(_frame())
    # Роль + кадр, но нет паспорта/устройства — чек-лист объясняет, чего не хватает
    assert not screen._capture_button.isEnabled()
    assert "паспорт" in screen._ready_label.text()

    screen._on_passports([_passport("p2", "approved")])
    screen._device_combo.addItem("dev", "d1")
    screen._calibration_combo.addItem("cal", "cal1")
    assert screen._capture_button.isEnabled()  # весь чек-лист закрыт
    assert "Готово" in screen._ready_label.text()


def test_user_role_keeps_capture_disabled(qapp, tmp_path):
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access([QuarryAccessEntry(
        quarry_id="q1", quarry_name="Карьер 1", role_name="user", role_level=1,
    )])
    screen = CaptureScreen(_context(tmp_path), state)
    screen._on_preview_frame(_frame())
    assert not screen._capture_button.isEnabled()


def test_passport_combo_excludes_drafts(qapp, tmp_path):
    screen = CaptureScreen(_context(tmp_path), AppState())
    screen._on_passports([
        _passport("p1", "draft"),
        _passport("p2", "approved"),
        _passport("p3", "active"),
        _passport("p4", "submitted"),
    ])
    ids = [screen._passport_combo.itemData(i) for i in range(screen._passport_combo.count())]
    assert ids == ["p2", "p3"]


def test_offline_capture_goes_to_queue(qapp, tmp_path):
    """Backend недоступен: кадр сохраняется на диск, операция в очереди SyncManager."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            raise httpx.ConnectError("down")
        return httpx.Response(200, json={"items": [], "total": 0, "page": 1, "page_size": 50})

    settings = Settings(offline_db_path=tmp_path / "offline.db")
    from zmetrics_desktop.offline.sync_manager import SyncManager

    context = SimpleNamespace(
        api=ApiClient(settings, transport=httpx.MockTransport(handler)),
        settings=settings,
        make_sync_manager=lambda: SyncManager(settings.offline_db_path),
    )
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access([QuarryAccessEntry(
        quarry_id="q1", quarry_name="Карьер 1", role_name="blaster", role_level=3,
    )])
    screen = CaptureScreen(context, state)
    screen._on_passports([_passport("p2", "approved")])
    screen._on_devices([])
    screen._device_combo.addItem("dev", "d1")
    screen._calibration_combo.addItem("cal", "cal1")
    screen._on_preview_frame(_frame())

    pytest.importorskip("cv2")  # encode_jpeg needs OpenCV
    screen._capture_and_send()

    assert "очереди" in screen._result_labels["job"].text()
    queue = SyncManager(settings.offline_db_path)
    items = queue.pending()
    assert len(items) == 1
    assert items[0].kind == "capture_upload"
    assert os.path.exists(items[0].payload["left_path"])  # кадр ждёт отправки на диске
    queue.close()
