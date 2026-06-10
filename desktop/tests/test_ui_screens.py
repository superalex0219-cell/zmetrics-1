"""Offscreen smoke tests for the quarries / sections screens.

Rendering handlers are called directly (not through QThreadPool) so the tests stay
deterministic; the network layer is a httpx MockTransport that returns empty pages.
"""
from __future__ import annotations

import os
from types import SimpleNamespace

import httpx
import pytest

from zmetrics_desktop.api.client import ApiClient
from zmetrics_desktop.config import Settings
from zmetrics_desktop.models import Quarry, SiteSection

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402 — after QT_QPA_PLATFORM

from zmetrics_desktop.ui.quarries import QuarriesScreen, optional_float  # noqa: E402
from zmetrics_desktop.ui.sections import SectionsScreen  # noqa: E402
from zmetrics_desktop.ui.state import AppState  # noqa: E402

_Q1 = Quarry(id="q1", name="Карьер 1", location_description="Сатка", latitude=55.0)
_Q2 = Quarry(id="q2", name="Карьер 2")
_S1 = SiteSection(id="s1", quarry_id="q1", name="Блок 3", block_number="3")


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    return app or QApplication([])


@pytest.fixture(autouse=True)
def sync_submit(monkeypatch):
    """Run ``submit`` inline — no QThreadPool, no cross-thread signals into widgets
    that the test has already destroyed (that crashes the interpreter)."""

    def run_inline(fn, on_success=None, on_error=None):
        try:
            result = fn()
        except Exception as exc:
            if on_error is not None:
                on_error(str(exc))
        else:
            if on_success is not None:
                on_success(result)

    monkeypatch.setattr("zmetrics_desktop.ui.quarries.submit", run_inline)
    monkeypatch.setattr("zmetrics_desktop.ui.sections.submit", run_inline)


def _context() -> SimpleNamespace:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": [], "total": 0, "page": 1, "page_size": 50})

    return SimpleNamespace(
        api=ApiClient(Settings(), transport=httpx.MockTransport(handler))
    )


# --- optional_float --------------------------------------------------------------------


def test_optional_float_empty_is_none():
    assert optional_float("") is None
    assert optional_float("   ") is None


def test_optional_float_accepts_comma():
    assert optional_float("55,16") == 55.16
    assert optional_float("61.4") == 61.4


def test_optional_float_rejects_garbage():
    with pytest.raises(ValueError):
        optional_float("abc")


# --- QuarriesScreen ----------------------------------------------------------------------


def test_quarries_table_renders_rows(qapp):
    screen = QuarriesScreen(_context(), AppState())
    screen._on_quarries([_Q1, _Q2])
    assert screen._table.rowCount() == 2
    assert screen._table.item(0, 0).text() == "Карьер 1"
    assert screen._table.item(0, 1).text() == "Сатка"
    assert screen._table.item(0, 2).text() == "55"
    assert screen._table.item(1, 2).text() == ""  # no latitude


def test_quarries_row_selection_publishes_state(qapp):
    state = AppState()
    screen = QuarriesScreen(_context(), state)
    screen._on_quarries([_Q1, _Q2])
    screen._table.selectRow(1)
    assert state.quarry is not None
    assert state.quarry.id == "q2"


def test_quarries_preselects_state_quarry(qapp):
    state = AppState()
    state.set_quarry(_Q2)
    screen = QuarriesScreen(_context(), state)
    screen._on_quarries([_Q1, _Q2])
    assert screen._table.currentRow() == 1


def test_quarries_create_requires_name(qapp):
    screen = QuarriesScreen(_context(), AppState())
    screen._create()
    assert screen._form_error.text() == "Укажите название"


def test_quarries_create_rejects_bad_latitude(qapp):
    screen = QuarriesScreen(_context(), AppState())
    screen._name_edit.setText("Новый")
    screen._lat_edit.setText("xx")
    screen._create()
    assert "xx" in screen._form_error.text()


# --- SectionsScreen ------------------------------------------------------------------------


def test_sections_combo_follows_state(qapp):
    state = AppState()
    state.set_quarry(_Q2)
    screen = SectionsScreen(_context(), state)
    screen._on_quarries([_Q1, _Q2])
    assert screen._quarry_combo.currentIndex() == 1


def test_sections_table_renders_rows(qapp):
    screen = SectionsScreen(_context(), AppState())
    screen._render_sections([_S1])
    assert screen._table.rowCount() == 1
    assert screen._table.item(0, 0).text() == "Блок 3"
    assert screen._table.item(0, 1).text() == "3"


def test_sections_external_quarry_change_moves_combo(qapp):
    state = AppState()
    screen = SectionsScreen(_context(), state)
    screen._loaded_once = True
    screen._on_quarries([_Q1, _Q2])
    state.set_quarry(_Q2)  # another screen switches the quarry
    assert screen._quarry_combo.currentIndex() == 1


def test_sections_create_requires_quarry(qapp):
    screen = SectionsScreen(_context(), AppState())
    screen._name_edit.setText("Блок 1")
    screen._create()
    assert screen._form_error.text() == "Сначала выберите карьер"


def test_sections_create_requires_name(qapp):
    state = AppState()
    state.set_quarry(_Q1)
    screen = SectionsScreen(_context(), state)
    screen._create()
    assert screen._form_error.text() == "Укажите название"
