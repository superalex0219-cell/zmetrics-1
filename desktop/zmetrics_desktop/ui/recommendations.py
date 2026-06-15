"""Recommendations screen: AI-предложения по БВР, read-only параметры, явное ревью.

SAFETY (жёсткие правила проекта):
- ``parameter_suggestions`` отображаются ТОЛЬКО как справочные значения — никакого
  копирования в паспорт, никаких кнопок «Применить»;
- смена статуса (принята/отклонена/рассмотрена) — только явный клик + подтверждение,
  с роли blaster; сервер пишет AuditLog;
- новые рекомендации всегда приходят в статусе «требует проверки человеком».
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from zmetrics_desktop.api.zmetrics import ZMetricsApi
from zmetrics_desktop.models import Quarry, Recommendation, Report
from zmetrics_desktop.ui.layout import (
    apply_screen_layout,
    configure_combo,
    configure_error_label,
    configure_wrapping_label,
)
from zmetrics_desktop.ui.state import ROLE_BLASTER
from zmetrics_desktop.ui.workers import submit

if TYPE_CHECKING:
    from zmetrics_desktop.context import AppContext
    from zmetrics_desktop.ui.state import AppState

REC_STATUS_RU = {
    "requires_human_review": "⚠ Требует проверки человеком",
    "reviewed": "Рассмотрена",
    "accepted": "Принята",
    "rejected": "Отклонена",
}

# Подписи параметров parameter_suggestions (единицы — как в домене).
PARAM_RU = {
    "burden_m": "ЛНС (burden), м",
    "spacing_m": "Расстояние в ряду (spacing), м",
    "stemming_m": "Забойка (stemming), м",
    "hole_depth_m": "Глубина скважины, м",
    "hole_diameter_mm": "Диаметр скважины, мм",
    "total_explosive_kg": "Общий заряд, кг",
    "specific_charge_kg_m3": "Удельный заряд, кг/м³",
    "target_p80_mm": "Целевой P80, мм",
}

# (status, button label, confirmation)
REVIEW_ACTIONS: list[tuple[str, str, str]] = [
    ("accepted", "Принять", "Отметить рекомендацию принятой? Запись попадёт в журнал аудита."),
    ("rejected", "Отклонить", "Отклонить рекомендацию?"),
    ("reviewed", "Рассмотрена", "Отметить рекомендацию рассмотренной?"),
]


def format_suggestions(suggestions: dict | None) -> str:
    """Справочный текст из parameter_suggestions — только для чтения."""
    if not suggestions:
        return "—"
    lines = []
    for key, value in suggestions.items():
        label = PARAM_RU.get(key, key)
        if isinstance(value, float):
            lines.append(f"• {label}: {value:g}")
        else:
            lines.append(f"• {label}: {value}")
    return "\n".join(lines)


class RecommendationsScreen(QWidget):
    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._api = ZMetricsApi(context.api)
        self._state = state
        self._loaded_once = False
        self._quarries: list[Quarry] = []
        self._reports: list[Report] = []
        self._recommendations: list[Recommendation] = []
        self._selected: Recommendation | None = None

        root = QVBoxLayout(self)
        apply_screen_layout(root)

        header = QHBoxLayout()
        header.addWidget(QLabel("Карьер:"))
        self._quarry_combo = QComboBox()
        configure_combo(self._quarry_combo, 140)
        self._quarry_combo.currentIndexChanged.connect(self._on_quarry_selected)
        header.addWidget(self._quarry_combo, stretch=1)
        header.addWidget(QLabel("Отчёт:"))
        self._report_combo = QComboBox()
        configure_combo(self._report_combo, 180)
        self._report_combo.currentIndexChanged.connect(self._on_report_selected)
        header.addWidget(self._report_combo, stretch=1)
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.refresh)
        header.addWidget(refresh)
        header.addStretch(1)
        root.addLayout(header)

        self._error_label = QLabel()
        configure_error_label(self._error_label)
        root.addWidget(self._error_label)

        splitter = QSplitter()
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Статус", "Дата", "Рекомендация"])
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

    def _build_detail_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(0)
        layout = QVBoxLayout(panel)

        self._status_label = QLabel("—")
        self._status_label.setStyleSheet("font-size: 15px; font-weight: 700; padding: 2px;")
        configure_wrapping_label(self._status_label)
        layout.addWidget(self._status_label)

        layout.addWidget(QLabel("Обоснование:"))
        self._text_view = QTextEdit()
        self._text_view.setReadOnly(True)
        layout.addWidget(self._text_view, stretch=2)

        params_title = QLabel("Предлагаемые параметры (справочно — не применяются автоматически):")
        configure_wrapping_label(params_title)
        layout.addWidget(params_title)
        self._params_view = QTextEdit()
        self._params_view.setReadOnly(True)
        layout.addWidget(self._params_view, stretch=1)

        self._review_info = QLabel("")
        configure_wrapping_label(self._review_info)
        layout.addWidget(self._review_info)

        notes_row = QHBoxLayout()
        notes_row.addWidget(QLabel("Заметка ревьюера:"))
        self._notes_edit = QLineEdit()
        notes_row.addWidget(self._notes_edit, stretch=1)
        layout.addLayout(notes_row)

        buttons = QHBoxLayout()
        self._review_buttons: dict[str, QPushButton] = {}
        for status, label, confirmation in REVIEW_ACTIONS:
            button = QPushButton(label)
            button.setVisible(False)
            button.clicked.connect(
                lambda _=False, s=status, c=confirmation: self._confirm_review(s, c)
            )
            self._review_buttons[status] = button
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self._action_error = QLabel()
        configure_error_label(self._action_error)
        layout.addWidget(self._action_error)
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
            self._on_reports([])

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
            self._on_reports,
            self._error_label.setText,
        )

    def _on_reports(self, reports: list[Report]) -> None:
        self._reports = reports
        self._report_combo.blockSignals(True)
        self._report_combo.clear()
        for report in reports:
            badge = "⚠ mock" if report.analysis_method == "mock" else "real"
            self._report_combo.addItem(
                f"{report.created_at[:10]} · {badge} · {report.title[:60]}", report.id
            )
        self._report_combo.blockSignals(False)
        if reports:
            self._report_combo.setCurrentIndex(0)
            self._load_recommendations(reports[0].id)
        else:
            self._render_recommendations([])

    def _on_report_selected(self, index: int) -> None:
        if 0 <= index < len(self._reports):
            self._load_recommendations(self._reports[index].id)

    def _load_recommendations(self, report_id: str) -> None:
        submit(
            lambda: self._api.list_recommendations(report_id),
            self._render_recommendations,
            self._error_label.setText,
        )

    def _render_recommendations(self, recommendations: list[Recommendation]) -> None:
        self._recommendations = recommendations
        selected_id = self._selected.id if self._selected else None
        self._table.blockSignals(True)
        self._table.setRowCount(len(recommendations))
        for row, rec in enumerate(recommendations):
            cells = [
                REC_STATUS_RU.get(rec.status, rec.status),
                rec.created_at[:10],
                rec.recommendation_text[:80],
            ]
            for col, text in enumerate(cells):
                self._table.setItem(row, col, QTableWidgetItem(text))
        self._table.blockSignals(False)

        self._selected = None
        for row, rec in enumerate(recommendations):
            if rec.id == selected_id:
                self._table.selectRow(row)
                break
        if self._selected is None:
            self._render_detail(None)

    # --- Detail -------------------------------------------------------------------

    def _on_row_selected(self) -> None:
        rows = {item.row() for item in self._table.selectedItems()}
        if len(rows) != 1:
            return
        row = rows.pop()
        if 0 <= row < len(self._recommendations):
            self._selected = self._recommendations[row]
            self._render_detail(self._selected)

    def _render_detail(self, rec: Recommendation | None) -> None:
        self._action_error.clear()
        if rec is None:
            self._status_label.setText("—")
            self._text_view.clear()
            self._params_view.clear()
            self._review_info.setText("")
            for button in self._review_buttons.values():
                button.setVisible(False)
            return

        self._status_label.setText(REC_STATUS_RU.get(rec.status, rec.status))
        self._status_label.setStyleSheet(
            "font-size: 15px; font-weight: 700; padding: 2px;"
            + (" color: #b06000;" if rec.status == "requires_human_review" else "")
        )
        self._text_view.setPlainText(rec.recommendation_text)
        self._params_view.setPlainText(format_suggestions(rec.parameter_suggestions))
        if rec.reviewed_at:
            notes = f" · {rec.reviewer_notes}" if rec.reviewer_notes else ""
            self._review_info.setText(f"Ревью: {rec.reviewed_at[:16].replace('T', ' ')}{notes}")
        else:
            self._review_info.setText("")

        self._apply_role_gating()

    def _apply_role_gating(self) -> None:
        rec = self._selected
        quarry_id = self._state.quarry.id if self._state.quarry else None
        can_review = (
            rec is not None
            and rec.status == "requires_human_review"
            and self._state.role_level(quarry_id) >= ROLE_BLASTER
        )
        for button in self._review_buttons.values():
            button.setVisible(can_review)

    # --- Review (explicit, confirmed) ------------------------------------------------

    def _confirm_review(self, status: str, confirmation: str) -> None:
        """SAFETY: ревью выполняется только после явного клика + подтверждения."""
        rec = self._selected
        if rec is None:
            return
        answer = QMessageBox.question(
            self, "Подтверждение", confirmation,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        notes = self._notes_edit.text().strip() or None
        self._action_error.clear()
        submit(
            lambda: self._api.review_recommendation(rec.report_id, rec.id, status, notes),
            self._on_reviewed,
            self._action_error.setText,
        )

    def _on_reviewed(self, rec: Recommendation) -> None:
        self._notes_edit.clear()
        self._selected = rec
        self._load_recommendations(rec.report_id)
