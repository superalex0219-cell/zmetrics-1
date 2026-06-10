"""Offscreen tests for the blast-passport screen: role gating, transitions, dialogs.

``submit`` is patched to run inline (no QThreadPool); the network is an httpx
MockTransport that records requests.
"""
from __future__ import annotations

import os
from types import SimpleNamespace

import httpx
import pytest

from zmetrics_desktop.api.client import ApiClient
from zmetrics_desktop.config import Settings
from zmetrics_desktop.models import BlastEvent, BlastPassport, Quarry, QuarryAccessEntry, SiteSection

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from zmetrics_desktop.ui.passports import (  # noqa: E402
    BlastEventDialog,
    PassportCreateDialog,
    PassportsScreen,
)
from zmetrics_desktop.ui.state import AppState  # noqa: E402

_Q1 = Quarry(id="q1", name="Карьер 1")
_S1 = SiteSection(id="s1", quarry_id="q1", name="Блок 3")


def _passport(status: str) -> BlastPassport:
    return BlastPassport(
        id="p1", site_section_id="s1", status=status, revision_number=1,
        target_p80_mm=300.0, created_at="2026-06-10T10:00:00Z",
        updated_at="2026-06-10T10:00:00Z",
    )


def _access(level: int) -> list[QuarryAccessEntry]:
    names = {1: "user", 2: "surveyor", 3: "blaster", 4: "admin"}
    return [QuarryAccessEntry(quarry_id="q1", quarry_name="Карьер 1",
                              role_name=names[level], role_level=level)]


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

    monkeypatch.setattr("zmetrics_desktop.ui.passports.submit", run_inline)


def _screen(state: AppState, requests: list[httpx.Request] | None = None) -> PassportsScreen:
    """Screen over a transport: blast-event GET → 404, list GETs → empty page,
    POST /{action} → the passport in the transitioned status."""

    def handler(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        path = request.url.path
        if path.endswith("/blast-event"):
            return httpx.Response(404, json={"detail": "No blast event for this passport"})
        if request.method == "POST":
            action = path.rsplit("/", 1)[-1]
            next_status = {"submit": "submitted", "approve": "approved",
                           "activate": "active", "complete": "completed"}[action]
            return httpx.Response(200, json=_passport(next_status).model_dump())
        return httpx.Response(200, json={"items": [], "total": 0, "page": 1, "page_size": 50})

    context = SimpleNamespace(api=ApiClient(Settings(), transport=httpx.MockTransport(handler)))
    return PassportsScreen(context, state)


def _select_first(screen: PassportsScreen, status: str) -> None:
    screen._render_passports([_S1], [_passport(status)])
    screen._table.selectRow(0)


# --- Role gating --------------------------------------------------------------------------


def test_no_access_hides_all_buttons(qapp):
    state = AppState()
    state.set_quarry(_Q1)  # access map empty → role 0 → fail closed
    screen = _screen(state)
    _select_first(screen, "draft")
    assert not screen._create_button.isVisibleTo(screen)
    assert all(not b.isVisibleTo(screen) for b in screen._transition_buttons.values())
    assert not screen._blast_button.isVisibleTo(screen)


def test_blaster_sees_submit_on_draft_only(qapp):
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access(_access(3))  # blaster
    screen = _screen(state)
    _select_first(screen, "draft")
    assert screen._create_button.isVisibleTo(screen)
    assert screen._transition_buttons["submit"].isVisibleTo(screen)
    assert not screen._transition_buttons["approve"].isVisibleTo(screen)


def test_blaster_cannot_approve_submitted(qapp):
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access(_access(3))
    screen = _screen(state)
    _select_first(screen, "submitted")
    assert not screen._transition_buttons["approve"].isVisibleTo(screen)


def test_admin_approves_submitted(qapp):
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access(_access(4))  # admin
    screen = _screen(state)
    _select_first(screen, "submitted")
    assert screen._transition_buttons["approve"].isVisibleTo(screen)
    assert not screen._transition_buttons["submit"].isVisibleTo(screen)


def test_existing_blast_event_is_rendered(qapp):
    """GET blast-event → 200: строка «Взрыв» заполняется, кнопка фиксации скрыта.

    JSON повторяет реальный ответ FastAPI (UUID/datetime строками, лишние поля)."""
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access(_access(3))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/blast-event"):
            return httpx.Response(200, json={
                "id": "5f0d8c7e-0000-0000-0000-000000000001",
                "passport_id": "p1",
                "executed_by_id": "5f0d8c7e-0000-0000-0000-000000000002",
                "blast_datetime": "2026-06-10T03:45:00Z",
                "actual_explosive_kg": 1250.0,
                "weather_conditions": None,
                "notes": None,
                "created_at": "2026-06-10T03:45:10.123456Z",
                "updated_at": "2026-06-10T03:45:10.123456Z",
            })
        return httpx.Response(200, json={"items": [], "total": 0, "page": 1, "page_size": 50})

    context = SimpleNamespace(api=ApiClient(Settings(), transport=httpx.MockTransport(handler)))
    screen = PassportsScreen(context, state)
    screen._render_passports([_S1], [_passport("active")])
    screen._table.selectRow(0)

    assert "2026-06-10 03:45" in screen._detail_labels["blast_event"].text()
    assert "1250" in screen._detail_labels["blast_event"].text()
    assert not screen._blast_button.isVisibleTo(screen)
    assert screen._error_label.text() == ""


def test_blast_button_only_without_existing_event(qapp):
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access(_access(3))
    screen = _screen(state)
    _select_first(screen, "approved")
    assert screen._blast_button.isVisibleTo(screen)  # blast-event GET returned 404

    screen._blast_event = BlastEvent(
        id="e1", passport_id="p1", executed_by_id="u1",
        blast_datetime="2026-06-10T12:00:00Z", created_at="2026-06-10T12:00:00Z",
    )
    screen._render_detail(screen._selected)
    assert not screen._blast_button.isVisibleTo(screen)


# --- Transitions ----------------------------------------------------------------------------


def test_transition_requires_confirmation(qapp, monkeypatch):
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access(_access(3))
    requests: list[httpx.Request] = []
    screen = _screen(state, requests)
    _select_first(screen, "draft")
    requests.clear()

    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No),
    )
    screen._confirm_transition("submit", "Отправить?")
    assert not any(r.method == "POST" for r in requests)  # отказ — никаких вызовов


def test_confirmed_transition_posts_action(qapp, monkeypatch):
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access(_access(3))
    requests: list[httpx.Request] = []
    screen = _screen(state, requests)
    _select_first(screen, "draft")
    requests.clear()

    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )
    screen._confirm_transition("submit", "Отправить?")
    posts = [r for r in requests if r.method == "POST"]
    assert len(posts) == 1
    assert posts[0].url.path == "/api/v1/quarries/q1/passports/p1/submit"


# --- Rendering -------------------------------------------------------------------------------


def test_table_renders_russian_status_and_section(qapp):
    state = AppState()
    state.set_quarry(_Q1)
    screen = _screen(state)
    screen._render_passports([_S1], [_passport("submitted")])
    assert screen._table.item(0, 0).text() == "На утверждении"
    assert screen._table.item(0, 2).text() == "Блок 3"
    assert screen._table.item(0, 4).text() == "300"


# --- Dialogs ---------------------------------------------------------------------------------


def test_create_dialog_validates_holes(qapp):
    dialog = PassportCreateDialog([_S1])
    dialog._edits["number_of_holes"].setText("abc")
    dialog._validate_and_accept()
    assert dialog.body is None
    assert "abc" in dialog._error.text()


def test_create_dialog_builds_body(qapp):
    dialog = PassportCreateDialog([_S1])
    dialog._edits["target_p80_mm"].setText("250,5")
    dialog._edits["number_of_holes"].setText("42")
    dialog._edits["explosive_type"].setText("Граммонит")
    dialog._validate_and_accept()
    assert dialog.body is not None
    assert dialog.body["site_section_id"] == "s1"
    assert dialog.body["target_p80_mm"] == 250.5
    assert dialog.body["number_of_holes"] == 42
    assert dialog.body["explosive_type"] == "Граммонит"
    assert dialog.body["burden_m"] is None  # никакого префилла


def test_blast_dialog_rejects_bad_datetime(qapp):
    dialog = BlastEventDialog()
    dialog._datetime_edit.setText("вчера")
    dialog._validate_and_accept()
    assert dialog.body is None
    assert dialog._error.text() != ""
