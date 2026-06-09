"""Shared UI state: the currently selected quarry.

Roles are per-quarry, so most screens scope their data to one quarry. The dashboard owns
the selector; other screens subscribe to ``quarry_changed``.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from zmetrics_desktop.models import Quarry


class AppState(QObject):
    quarry_changed = Signal(object)  # Quarry | None

    def __init__(self) -> None:
        super().__init__()
        self.quarry: Quarry | None = None

    def set_quarry(self, quarry: Quarry | None) -> None:
        if quarry is not None and self.quarry is not None and quarry.id == self.quarry.id:
            self.quarry = quarry  # refreshed payload, same selection — no signal
            return
        self.quarry = quarry
        self.quarry_changed.emit(quarry)
