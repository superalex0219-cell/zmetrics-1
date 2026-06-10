"""Background execution helper: run a callable on QThreadPool, signal back to the UI.

Every network call from a screen goes through ``submit`` — never block the Qt event
loop. Error messages are emitted as strings (the screen decides how to surface them).

The worker is kept in a module-level registry until its signal is delivered: QThreadPool
auto-deletes the QRunnable right after ``run()``, and if Python then collects the
``signals`` QObject before the main loop processes the queued emit, the callback is
silently dropped (intermittent «data never arrives» bugs).
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

# Workers waiting for their queued signal to be processed by the UI thread.
_active: set[FnWorker] = set()


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
    # Release the keep-alive AFTER the user callback (slots run in connection order).
    _active.add(worker)
    worker.signals.succeeded.connect(lambda _result=None: _active.discard(worker))
    worker.signals.failed.connect(lambda _message=None: _active.discard(worker))
    QThreadPool.globalInstance().start(worker)
    return worker
