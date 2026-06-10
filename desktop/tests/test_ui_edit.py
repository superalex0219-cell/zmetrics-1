"""EDIT-1: универсальный диалог редактирования + ролевой гейтинг кнопок «Изменить»."""
from __future__ import annotations

import os
from types import SimpleNamespace

import httpx
import pytest

from zmetrics_desktop.api.client import ApiClient
from zmetrics_desktop.config import Settings
from zmetrics_desktop.models import BlastEvent, BlastPassport, Quarry, QuarryAccessEntry

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from zmetrics_desktop.ui.edit_dialogs import EditFormDialog  # noqa: E402
from zmetrics_desktop.ui.passports import PassportsScreen  # noqa: E402
from zmetrics_desktop.ui.quarries import QuarriesScreen  # noqa: E402
from zmetrics_desktop.ui.state import AppState  # noqa: E402

_Q1 = Quarry(id="q1", name="Карьер 1")


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    return app or QApplication([])


def _context() -> SimpleNamespace:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": [], "total": 0, "page": 1, "page_size": 50})

    settings = Settings()
    return SimpleNamespace(api=ApiClient(settings, transport=httpx.MockTransport(handler)))


def _access(role: str, level: int) -> list[QuarryAccessEntry]:
    return [QuarryAccessEntry(
        quarry_id="q1", quarry_name="Карьер 1", role_name=role, role_level=level,
    )]


def _passport(status: str) -> BlastPassport:
    return BlastPassport(
        id="p1", site_section_id="s1", status=status, revision_number=1,
        target_p80_mm=400.0, created_at="2026-06-11", updated_at="2026-06-11",
    )


# --- EditFormDialog -------------------------------------------------------------------


def test_edit_dialog_collects_only_changed_fields(qapp):
    dialog = EditFormDialog("t", [
        ("name", "Название:", "Старое", "str"),
        ("lat", "Широта:", 55.5, "float"),
        ("holes", "Скважин:", 10, "int"),
    ])
    dialog._edits["name"].setText("Новое")
    dialog._validate_and_accept()
    assert dialog.changes == {"name": "Новое"}  # lat/holes не тронуты


def test_edit_dialog_empty_becomes_none(qapp):
    dialog = EditFormDialog("t", [("notes", "Прим.:", "было", "str")])
    dialog._edits["notes"].setText("")
    dialog._validate_and_accept()
    assert dialog.changes == {"notes": None}


def test_edit_dialog_rejects_bad_number(qapp):
    dialog = EditFormDialog("t", [("lat", "Широта:", None, "float")])
    dialog._edits["lat"].setText("abc")
    dialog._validate_and_accept()
    assert dialog.changes is None  # не принято
    assert dialog._error.text()


# --- Role gating ------------------------------------------------------------------------


def test_quarry_edit_button_requires_admin(qapp):
    state = AppState()
    screen = QuarriesScreen(_context(), state)
    screen._on_quarries([_Q1])
    screen._table.selectRow(0)

    state.set_access(_access("blaster", 3))
    screen._update_edit_button()
    assert not screen._edit_button.isVisible() or not screen._edit_button.isVisibleTo(screen)

    state.set_access(_access("admin", 4))
    screen._update_edit_button()
    assert screen._edit_button.isVisibleTo(screen)


def test_passport_edit_buttons_draft_only(qapp):
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access(_access("blaster", 3))
    screen = PassportsScreen(_context(), state)

    screen._selected = _passport("draft")
    screen._render_detail(screen._selected)
    assert screen._edit_draft_button.isVisibleTo(screen)

    screen._selected = _passport("approved")
    screen._render_detail(screen._selected)
    assert not screen._edit_draft_button.isVisibleTo(screen)  # только ревизией


def test_blast_edit_button_needs_event_and_role(qapp):
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access(_access("user", 1))
    screen = PassportsScreen(_context(), state)
    screen._selected = _passport("active")
    screen._blast_event = BlastEvent(
        id="e1", passport_id="p1", executed_by_id="u1",
        blast_datetime="2026-06-11T10:00:00Z", created_at="2026-06-11",
    )
    screen._render_detail(screen._selected)
    assert not screen._edit_blast_button.isVisibleTo(screen)  # роль user — нельзя

    state.set_access(_access("blaster", 3))
    screen._render_detail(screen._selected)
    assert screen._edit_blast_button.isVisibleTo(screen)
