"""Background execution helper: run a callable on QThreadPool, signal back to the UI.

Every network call from a screen goes through ``submit`` — never block the Qt event
loop. Error messages are emitted as strings (the screen decides how to surface them).
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class FnWorker(QRunnable):
    class Signals(QObject):
        succeeded = Signal(object)
        failed = Signal(str)

    def __init__(self, fn: Callable[[], Any]) -> None:
        super().__init__()
        self._fn = fn
        self.signals = self.Signals()

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as exc:  # ApiError, httpx errors, validation errors
            self.signals.failed.emit(str(exc))
        else:
            self.signals.succeeded.emit(result)


def submit(
    fn: Callable[[], Any],
    on_success: Callable[[Any], None] | None = None,
    on_error: Callable[[str], None] | None = None,
) -> FnWorker:
    """Schedule ``fn`` on the global thread pool; connect callbacks before it starts."""
    worker = FnWorker(fn)
    if on_success is not None:
        worker.signals.succeeded.connect(on_success)
    if on_error is not None:
        worker.signals.failed.connect(on_error)
    QThreadPool.globalInstance().start(worker)
    return worker
