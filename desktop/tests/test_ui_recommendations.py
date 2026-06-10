"""Offscreen tests for the recommendations screen: read-only params, explicit review."""
from __future__ import annotations

import json
import os
from types import SimpleNamespace

import httpx
import pytest

from zmetrics_desktop.api.client import ApiClient
from zmetrics_desktop.config import Settings
from zmetrics_desktop.models import Quarry, QuarryAccessEntry, Recommendation

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from zmetrics_desktop.ui.recommendations import (  # noqa: E402
    RecommendationsScreen,
    format_suggestions,
)
from zmetrics_desktop.ui.state import AppState  # noqa: E402

_Q1 = Quarry(id="q1", name="Карьер 1")


def _rec(status: str) -> Recommendation:
    return Recommendation(
        id="rec1", report_id="r1", status=status,
        recommendation_text="Уменьшить ЛНС для целевого P80.",
        parameter_suggestions={"burden_m": 3.2, "spacing_m": 4.0},
        created_at="2026-06-10T12:00:00Z",
    )


def _access(level: int) -> list[QuarryAccessEntry]:
    return [QuarryAccessEntry(quarry_id="q1", quarry_name="Карьер 1",
                              role_name="x", role_level=level)]


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

    monkeypatch.setattr("zmetrics_desktop.ui.recommendations.submit", run_inline)


def _screen(state: AppState, requests: list[httpx.Request] | None = None) -> RecommendationsScreen:
    def handler(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        if request.url.path.endswith("/review"):
            body = json.loads(request.read())
            reviewed = dict(_rec(body["status"]).model_dump(),
                            reviewer_notes=body.get("reviewer_notes"),
                            reviewed_at="2026-06-10T13:00:00Z")
            return httpx.Response(200, json=reviewed)
        return httpx.Response(200, json={"items": [], "total": 0, "page": 1, "page_size": 50})

    context = SimpleNamespace(api=ApiClient(Settings(), transport=httpx.MockTransport(handler)))
    return RecommendationsScreen(context, state)


def test_format_suggestions_is_reference_text():
    text = format_suggestions({"burden_m": 3.2, "unknown_key": "x"})
    assert "ЛНС (burden), м: 3.2" in text
    assert "unknown_key: x" in text
    assert format_suggestions(None) == "—"


def test_requires_review_status_and_readonly_params(qapp):
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access(_access(3))
    screen = _screen(state)
    screen._render_recommendations([_rec("requires_human_review")])
    screen._table.selectRow(0)

    assert "Требует проверки" in screen._status_label.text()
    assert screen._params_view.isReadOnly()
    assert "3.2" in screen._params_view.toPlainText()
    assert all(b.isVisibleTo(screen) for b in screen._review_buttons.values())


def test_review_buttons_hidden_for_user_role(qapp):
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access(_access(1))  # user
    screen = _screen(state)
    screen._render_recommendations([_rec("requires_human_review")])
    screen._table.selectRow(0)
    assert all(not b.isVisibleTo(screen) for b in screen._review_buttons.values())


def test_review_buttons_hidden_when_already_reviewed(qapp):
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access(_access(4))  # даже admin не ревьюит повторно
    screen = _screen(state)
    screen._render_recommendations([_rec("accepted")])
    screen._table.selectRow(0)
    assert all(not b.isVisibleTo(screen) for b in screen._review_buttons.values())


def test_declined_confirmation_sends_nothing(qapp, monkeypatch):
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access(_access(3))
    requests: list[httpx.Request] = []
    screen = _screen(state, requests)
    screen._render_recommendations([_rec("requires_human_review")])
    screen._table.selectRow(0)
    requests.clear()

    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))
    screen._confirm_review("accepted", "Принять?")
    assert not any(r.method == "POST" for r in requests)


def test_confirmed_review_posts_status_and_notes(qapp, monkeypatch):
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access(_access(3))
    requests: list[httpx.Request] = []
    screen = _screen(state, requests)
    screen._render_recommendations([_rec("requires_human_review")])
    screen._table.selectRow(0)
    screen._notes_edit.setText("согласовано с маркшейдером")
    requests.clear()

    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    screen._confirm_review("accepted", "Принять?")

    posts = [r for r in requests if r.method == "POST"]
    assert len(posts) == 1
    assert posts[0].url.path == "/api/v1/reports/r1/recommendations/rec1/review"
    body = json.loads(posts[0].read())
    assert body == {"status": "accepted", "reviewer_notes": "согласовано с маркшейдером"}
