"""End-to-end delivery test for the QThreadPool helper.

Regression for the dropped-callback bug: ``submit`` used to discard the worker, the
runnable got auto-deleted after ``run()`` and the queued signal could die with the
GC-ed ``signals`` QObject before the UI thread processed it.
"""
from __future__ import annotations

import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QThreadPool  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from zmetrics_desktop.ui.workers import submit  # noqa: E402


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    return app or QApplication([])


def _spin_until(app: QApplication, condition, timeout_s: float = 5.0) -> None:
    deadline = time.monotonic() + timeout_s
    while not condition() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


def test_success_callback_is_delivered(qapp):
    results: list[object] = []
    for i in range(20):  # many in a row — the old bug was timing-dependent
        submit(lambda i=i: i, results.append)
    _spin_until(qapp, lambda: len(results) == 20)
    QThreadPool.globalInstance().waitForDone(2000)
    assert sorted(results) == list(range(20))  # type: ignore[type-var]


def test_error_callback_is_delivered(qapp):
    errors: list[str] = []

    def boom() -> None:
        raise RuntimeError("сломалось")

    submit(boom, on_error=errors.append)
    _spin_until(qapp, lambda: errors)
    assert errors == ["сломалось"]
