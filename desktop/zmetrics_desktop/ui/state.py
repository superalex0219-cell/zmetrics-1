"""Shared UI state: the currently selected quarry + the caller's per-quarry roles.

Roles are per-quarry, so most screens scope their data to one quarry. The dashboard owns
the selector; other screens subscribe to ``quarry_changed``.

Role levels mirror the backend (``user < surveyor < blaster < admin``). The access map
gates buttons only — every call is re-checked server-side, so an out-of-date map can at
worst show a button that then gets a 403.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from zmetrics_desktop.models import Quarry, QuarryAccessEntry

ROLE_USER = 1
ROLE_SURVEYOR = 2
ROLE_BLASTER = 3
ROLE_ADMIN = 4


class AppState(QObject):
    quarry_changed = Signal(object)  # Quarry | None
    access_changed = Signal()
    # Экраны просят перезагрузить карту доступов (например, после создания карьера —
    # бэкенд выдал создателю admin, но /me/access грузился ещё при логине).
    access_refresh_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.quarry: Quarry | None = None
        self._access: dict[str, int] = {}

    def set_quarry(self, quarry: Quarry | None) -> None:
        if quarry is not None and self.quarry is not None and quarry.id == self.quarry.id:
            self.quarry = quarry  # refreshed payload, same selection — no signal
            return
        self.quarry = quarry
        self.quarry_changed.emit(quarry)

    def request_access_refresh(self) -> None:
        self.access_refresh_requested.emit()

    def set_access(self, entries: list[QuarryAccessEntry]) -> None:
        self._access = {entry.quarry_id: entry.role_level for entry in entries}
        self.access_changed.emit()

    def role_level(self, quarry_id: str | None) -> int:
        """0 when unknown — fail closed: buttons stay hidden until access is loaded."""
        if quarry_id is None:
            return 0
        return self._access.get(quarry_id, 0)
