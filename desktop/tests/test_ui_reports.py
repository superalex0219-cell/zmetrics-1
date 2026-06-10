"""Offscreen tests for the reports screen: mock badge, detail, export gating + file."""
from __future__ import annotations

import json
import os
from types import SimpleNamespace

import httpx
import pytest

from zmetrics_desktop.api.client import ApiClient
from zmetrics_desktop.config import Settings
from zmetrics_desktop.models import AnalysisResult, Quarry, QuarryAccessEntry, Report, SizeBin

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFileDialog  # noqa: E402

from zmetrics_desktop.ui.reports import ReportsScreen  # noqa: E402
from zmetrics_desktop.ui.state import AppState  # noqa: E402

_Q1 = Quarry(id="q1", name="Карьер 1")
_REPORT = Report(
    id="r1", title="⚠ Mock pipeline — Granulometric Analysis", report_type="granulometric",
    analysis_method="mock", analysis_result_id="ar1", confidence_score=0.72,
    created_at="2026-06-10T12:00:00Z",
)
_RESULT = AnalysisResult(
    id="ar1", p10_mm=95.2, p50_mm=210.7, p80_mm=312.4,
    rosin_rammler_n=1.8, rosin_rammler_xc=240.0,
    oversize_percent=4.2, fines_percent=8.1, confidence_score=0.72,
    confidence_notes="⚠ Mock pipeline — results are synthetic",
    size_distribution=[SizeBin(size_mm=100, cumulative_passing_pct=12.5)],
)


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

    monkeypatch.setattr("zmetrics_desktop.ui.reports.submit", run_inline)


def _screen(state: AppState) -> ReportsScreen:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/v1/analysis-results/ar1":
            return httpx.Response(200, json=_RESULT.model_dump())
        if path == "/api/v1/reports/r1/export":
            return httpx.Response(200, json={"report": {"id": "r1"}, "note": "⚠ Mock"})
        return httpx.Response(200, json={"items": [], "total": 0, "page": 1, "page_size": 50})

    context = SimpleNamespace(api=ApiClient(Settings(), transport=httpx.MockTransport(handler)))
    return ReportsScreen(context, state)


def _access(level: int) -> list[QuarryAccessEntry]:
    return [QuarryAccessEntry(quarry_id="q1", quarry_name="Карьер 1",
                              role_name="x", role_level=level)]


def test_table_shows_mock_method(qapp):
    state = AppState()
    state.set_quarry(_Q1)
    screen = _screen(state)
    screen._render_reports([_REPORT])
    assert screen._table.item(0, 2).text() == "⚠ mock"
    assert screen._table.item(0, 0).text() == "2026-06-10"


def test_detail_renders_result_and_badge(qapp):
    state = AppState()
    state.set_quarry(_Q1)
    screen = _screen(state)
    screen._render_reports([_REPORT])
    screen._table.selectRow(0)  # sync submit загрузит результат сразу
    assert "MOCK" in screen._method_badge.text()
    assert screen._detail_labels["p80"].text() == "312.4 мм"
    assert "n = 1.8" in screen._detail_labels["rr"].text()
    assert "синтетические" in screen._detail_labels["notes"].text().lower() or \
           "synthetic" in screen._detail_labels["notes"].text().lower()


def test_export_hidden_below_blaster(qapp):
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access(_access(2))  # surveyor
    screen = _screen(state)
    screen._render_reports([_REPORT])
    screen._table.selectRow(0)
    assert not screen._export_button.isVisibleTo(screen)


def test_export_writes_json_file(qapp, tmp_path, monkeypatch):
    state = AppState()
    state.set_quarry(_Q1)
    state.set_access(_access(3))  # blaster
    screen = _screen(state)
    screen._render_reports([_REPORT])
    screen._table.selectRow(0)
    assert screen._export_button.isVisibleTo(screen)

    target = tmp_path / "report.json"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *a, **k: (str(target), "JSON (*.json)")),
    )
    screen._export_json()

    saved = json.loads(target.read_text(encoding="utf-8"))
    assert saved["report"]["id"] == "r1"
    assert "⚠" in saved["note"]
