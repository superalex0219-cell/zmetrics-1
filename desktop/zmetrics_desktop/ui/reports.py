"""Reports screen: list per quarry, analysis detail, export, mock badge.

Метод анализа (mock/real) показывается крупно и явно — отчёты mock-пайплайна помечены
«⚠ Синтетические данные». Экспорт (PDF/DOCX/XLSX/CSV/JSON, REPORT-X) доступен
с роли blaster (серверная проверка дублируется гейтингом кнопки).
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from zmetrics_desktop.api.zmetrics import ZMetricsApi
from zmetrics_desktop.models import AnalysisResult, Quarry, Report
from zmetrics_desktop.ui.charts import HistogramWidget
from zmetrics_desktop.ui.passports import _fmt
from zmetrics_desktop.ui.state import ROLE_BLASTER
from zmetrics_desktop.ui.workers import submit

if TYPE_CHECKING:
    from zmetrics_desktop.context import AppContext
    from zmetrics_desktop.ui.state import AppState


class ReportsScreen(QWidget):
    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._api = ZMetricsApi(context.api)
        self._state = state
        self._loaded_once = False
        self._quarries: list[Quarry] = []
        self._reports: list[Report] = []
        self._selected: Report | None = None

        root = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addWidget(QLabel("Карьер:"))
        self._quarry_combo = QComboBox()
        self._quarry_combo.setMinimumWidth(280)
        self._quarry_combo.currentIndexChanged.connect(self._on_quarry_selected)
        header.addWidget(self._quarry_combo)
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.refresh)
        header.addWidget(refresh)
        header.addStretch(1)
        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: #b00;")
        header.addWidget(self._error_label)
        root.addLayout(header)

        splitter = QSplitter()
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Дата", "Заголовок", "Метод", "Confidence"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.itemSelectionChanged.connect(self._on_row_selected)
        splitter.addWidget(self._table)
        splitter.addWidget(self._build_detail_panel())
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter, stretch=1)

        self._state.quarry_changed.connect(self._on_state_quarry_changed)
        self._state.access_changed.connect(self._apply_role_gating)
        self._apply_role_gating()

    def _build_detail_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Метод анализа — крупно и заметно (правило безопасности: mock помечается всегда)
        self._method_badge = QLabel("")
        self._method_badge.setStyleSheet("font-size: 16px; font-weight: 700; padding: 4px;")
        layout.addWidget(self._method_badge)

        box = QGroupBox("Результат анализа")
        form = QFormLayout(box)
        self._detail_labels: dict[str, QLabel] = {}
        for key, label in [
            ("p10", "P10:"),
            ("p50", "P50:"),
            ("p80", "P80:"),
            ("rr", "Розин-Раммлер (n / xc):"),
            ("oversize", "Негабарит:"),
            ("fines", "Мелочь:"),
            ("confidence", "Confidence:"),
            ("notes", "Примечания:"),
            ("model", "Версия модели:"),
        ]:
            value = QLabel("—")
            value.setWordWrap(True)
            self._detail_labels[key] = value
            form.addRow(label, value)
        layout.addWidget(box)

        self._histogram = HistogramWidget()
        layout.addWidget(self._histogram, stretch=1)

        self._format_label = QLabel("Формат:")
        self._format_combo = QComboBox()
        for label, fmt in [
            ("PDF", "pdf"),
            ("Word (DOCX)", "docx"),
            ("Excel (XLSX)", "xlsx"),
            ("CSV", "csv"),
            ("JSON", "json"),
        ]:
            self._format_combo.addItem(label, fmt)
        self._export_button = QPushButton("Экспорт…")
        self._export_button.clicked.connect(self._export)
        for widget in (self._format_label, self._format_combo, self._export_button):
            widget.setVisible(False)  # blaster+
        export_row = QHBoxLayout()
        export_row.addWidget(self._format_label)
        export_row.addWidget(self._format_combo)
        export_row.addWidget(self._export_button)
        export_row.addStretch(1)
        layout.addLayout(export_row)
        return panel

    # --- Loading ------------------------------------------------------------------

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 — Qt naming
        super().showEvent(event)
        if not self._loaded_once:
            self._loaded_once = True
            self.refresh()

    def refresh(self) -> None:
        self._error_label.clear()
        submit(self._api.list_quarries, self._on_quarries, self._error_label.setText)

    def _on_quarries(self, quarries: list[Quarry]) -> None:
        self._quarries = quarries
        current_id = self._state.quarry.id if self._state.quarry else None
        self._quarry_combo.blockSignals(True)
        self._quarry_combo.clear()
        for quarry in quarries:
            self._quarry_combo.addItem(quarry.name, quarry.id)
        index = next(
            (i for i, q in enumerate(quarries) if q.id == current_id), 0 if quarries else -1
        )
        if index >= 0:
            self._quarry_combo.setCurrentIndex(index)
        self._quarry_combo.blockSignals(False)

        if quarries:
            self._state.set_quarry(quarries[index])
            self._load_reports(quarries[index])
        else:
            self._state.set_quarry(None)
            self._render_reports([])

    def _on_quarry_selected(self, index: int) -> None:
        if 0 <= index < len(self._quarries):
            quarry = self._quarries[index]
            self._state.set_quarry(quarry)
            self._load_reports(quarry)

    def _on_state_quarry_changed(self, quarry: object) -> None:
        if quarry is None or not self._loaded_once:
            return
        for i in range(self._quarry_combo.count()):
            if self._quarry_combo.itemData(i) == quarry.id:
                if i != self._quarry_combo.currentIndex():
                    self._quarry_combo.blockSignals(True)
                    self._quarry_combo.setCurrentIndex(i)
                    self._quarry_combo.blockSignals(False)
                    self._load_reports(quarry)  # type: ignore[arg-type]
                return
        self.refresh()

    def _load_reports(self, quarry: Quarry) -> None:
        submit(
            lambda: self._api.list_reports(quarry.id),
            self._render_reports,
            self._error_label.setText,
        )

    def _render_reports(self, reports: list[Report]) -> None:
        self._reports = reports
        self._table.blockSignals(True)
        self._table.setRowCount(len(reports))
        for row, report in enumerate(reports):
            method = "⚠ mock" if report.analysis_method == "mock" else "real"
            cells = [
                report.created_at[:10],
                report.title,
                method,
                _fmt(report.confidence_score),
            ]
            for col, text in enumerate(cells):
                self._table.setItem(row, col, QTableWidgetItem(text))
        self._table.blockSignals(False)
        self._selected = None
        self._render_detail(None, None)

    # --- Detail -------------------------------------------------------------------

    def _on_row_selected(self) -> None:
        rows = {item.row() for item in self._table.selectedItems()}
        if len(rows) != 1:
            return
        row = rows.pop()
        if not (0 <= row < len(self._reports)):
            return
        report = self._reports[row]
        self._selected = report
        self._render_detail(report, None)
        submit(
            lambda: self._api.get_analysis_result(report.analysis_result_id),
            lambda result, r=report: self._on_result(r, result),
            self._error_label.setText,
        )

    def _on_result(self, report: Report, result: object) -> None:
        if self._selected is None or self._selected.id != report.id:
            return  # selection moved on while loading
        self._render_detail(report, result)  # type: ignore[arg-type]

    def _render_detail(self, report: Report | None, result: AnalysisResult | None) -> None:
        labels = self._detail_labels
        if report is None:
            self._method_badge.setText("")
            for value in labels.values():
                value.setText("—")
            self._histogram.set_bins([])
            self._apply_role_gating()
            return

        if report.analysis_method == "mock":
            self._method_badge.setText("⚠ MOCK-ПАЙПЛАЙН — СИНТЕТИЧЕСКИЕ ДАННЫЕ")
            self._method_badge.setStyleSheet(
                "font-size: 16px; font-weight: 700; padding: 4px; color: #b06000;"
            )
        else:
            self._method_badge.setText("Реальный CV-пайплайн")
            self._method_badge.setStyleSheet(
                "font-size: 16px; font-weight: 700; padding: 4px; color: #2e7d32;"
            )
        labels["model"].setText(_fmt(report.model_version_tag))

        if result is None:
            for key in ("p10", "p50", "p80", "rr", "oversize", "fines", "confidence", "notes"):
                labels[key].setText("загрузка…")
            self._histogram.set_bins([])
        else:
            labels["p10"].setText(_fmt(result.p10_mm, " мм"))
            labels["p50"].setText(_fmt(result.p50_mm, " мм"))
            labels["p80"].setText(_fmt(result.p80_mm, " мм"))
            n = _fmt(result.rosin_rammler_n)
            xc = _fmt(result.rosin_rammler_xc, " мм")
            labels["rr"].setText(f"n = {n} · xc = {xc}")
            labels["oversize"].setText(_fmt(result.oversize_percent, " %"))
            labels["fines"].setText(_fmt(result.fines_percent, " %"))
            labels["confidence"].setText(_fmt(result.confidence_score))
            labels["notes"].setText(_fmt(result.confidence_notes))
            self._histogram.set_bins(result.size_distribution or [])
        self._apply_role_gating()

    def _apply_role_gating(self) -> None:
        quarry_id = self._state.quarry.id if self._state.quarry else None
        visible = (
            self._selected is not None
            and self._state.role_level(quarry_id) >= ROLE_BLASTER
        )
        for widget in (self._format_label, self._format_combo, self._export_button):
            widget.setVisible(visible)

    # --- Export ----------------------------------------------------------------------

    _EXPORT_FILTERS = {
        "pdf": "PDF (*.pdf)",
        "docx": "Word (*.docx)",
        "xlsx": "Excel (*.xlsx)",
        "csv": "CSV (*.csv)",
        "json": "JSON (*.json)",
    }

    def _export(self) -> None:
        report = self._selected
        fmt = self._format_combo.currentData()
        if report is None or not fmt:
            return
        default_name = f"report_{report.id[:8]}_{report.created_at[:10]}.{fmt}"
        path, _filter = QFileDialog.getSaveFileName(
            self, "Сохранить отчёт", default_name, self._EXPORT_FILTERS[fmt]
        )
        if not path:
            return
        self._error_label.clear()
        self._export_button.setEnabled(False)

        def export() -> str:
            content = self._api.export_report(report.id, fmt)
            Path(path).write_bytes(content)
            return path

        def done(_saved: object) -> None:
            self._export_button.setEnabled(True)
            self._error_label.setText("")

        def failed(message: str) -> None:
            self._export_button.setEnabled(True)
            self._error_label.setText(message)

        submit(export, done, failed)
