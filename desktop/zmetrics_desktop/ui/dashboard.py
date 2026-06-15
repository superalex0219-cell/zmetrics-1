"""Dashboard screen: quarry selector, metric cards, P80, fraction histogram, recent
reports. Parity with the former web dashboard (counters + size distribution + latest
reports with the mock/real badge)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from zmetrics_desktop.api.zmetrics import ZMetricsApi
from zmetrics_desktop.models import AnalysisResult, Quarry, Report
from zmetrics_desktop.ui.charts import HistogramWidget
from zmetrics_desktop.ui.workers import submit

if TYPE_CHECKING:
    from zmetrics_desktop.context import AppContext
    from zmetrics_desktop.ui.state import AppState


class _MetricCard(QFrame):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self)
        self._value = QLabel("—")
        self._value.setStyleSheet("font-size: 24px; font-weight: 600;")
        self._value.setMinimumWidth(0)
        caption = QLabel(label)
        caption.setStyleSheet("color: gray;")
        caption.setWordWrap(True)
        caption.setMinimumWidth(0)
        layout.addWidget(self._value)
        layout.addWidget(caption)

    def set_value(self, value: str) -> None:
        self._value.setText(value)


_HistogramWidget = HistogramWidget  # перенесён в ui/charts.py; имя сохранено для экрана


class DashboardScreen(QWidget):
    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._api = ZMetricsApi(context.api)
        self._state = state
        self._loaded_once = False
        self._quarries: list[Quarry] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # Header: quarry selector + refresh
        header = QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(QLabel("Карьер:"))
        self._quarry_combo = QComboBox()
        self._quarry_combo.setMinimumWidth(160)
        self._quarry_combo.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.Fixed,
        )
        self._quarry_combo.currentIndexChanged.connect(self._on_quarry_selected)
        header.addWidget(self._quarry_combo, stretch=1)
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.refresh)
        header.addWidget(refresh)
        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: #b00;")
        self._error_label.setWordWrap(True)
        self._error_label.setMinimumWidth(0)
        self._error_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        header.addWidget(self._error_label, stretch=2)
        root.addLayout(header)

        # Metric cards
        cards = QGridLayout()
        cards.setHorizontalSpacing(12)
        cards.setVerticalSpacing(12)
        self._card_quarries = _MetricCard("Карьеры")
        self._card_sections = _MetricCard("Участки")
        self._card_reports = _MetricCard("Отчёты")
        self._card_p80 = _MetricCard("P80 (последний анализ)")
        for index, card in enumerate((
            self._card_quarries,
            self._card_sections,
            self._card_reports,
            self._card_p80,
        )):
            cards.addWidget(card, index // 2, index % 2)
        cards.setColumnStretch(0, 1)
        cards.setColumnStretch(1, 1)
        root.addLayout(cards)

        # Body: histogram + recent reports
        body = QGridLayout()
        hist_box = QVBoxLayout()
        hist_title = QLabel("Распределение фракций")
        hist_title.setStyleSheet("font-weight: 600;")
        self._histogram = _HistogramWidget()
        hist_box.addWidget(hist_title)
        hist_box.addWidget(self._histogram, stretch=1)

        reports_box = QVBoxLayout()
        reports_title = QLabel("Последние отчёты")
        reports_title.setStyleSheet("font-weight: 600;")
        self._reports_list = QListWidget()
        reports_box.addWidget(reports_title)
        reports_box.addWidget(self._reports_list, stretch=1)

        hist_holder, reports_holder = QWidget(), QWidget()
        hist_holder.setMinimumWidth(0)
        reports_holder.setMinimumWidth(0)
        hist_holder.setLayout(hist_box)
        reports_holder.setLayout(reports_box)
        self._histogram.setMinimumWidth(0)
        self._reports_list.setMinimumWidth(0)
        self._reports_list.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        body.addWidget(hist_holder, 0, 0)
        body.addWidget(reports_holder, 0, 1)
        body.setColumnStretch(0, 3)
        body.setColumnStretch(1, 2)
        root.addLayout(body, stretch=1)

        self._state.quarry_changed.connect(self._on_state_quarry_changed)

    # --- Loading ----------------------------------------------------------------------

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 — Qt naming
        super().showEvent(event)
        if not self._loaded_once:
            self._loaded_once = True
            self.refresh()

    def refresh(self) -> None:
        self._error_label.clear()
        submit(self._api.list_quarries, self._on_quarries, self._on_error)

    def _on_quarries(self, quarries: list[Quarry]) -> None:
        self._quarries = quarries
        self._card_quarries.set_value(str(len(quarries)))

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
            self._load_quarry_data(quarries[index])
        else:
            self._state.set_quarry(None)
            self._show_empty()

    def _on_quarry_selected(self, index: int) -> None:
        if 0 <= index < len(self._quarries):
            quarry = self._quarries[index]
            self._state.set_quarry(quarry)
            self._load_quarry_data(quarry)

    def _on_state_quarry_changed(self, quarry: object) -> None:
        """Another screen changed the selection — follow it without re-emitting."""
        if quarry is None or not self._loaded_once:
            return
        for i in range(self._quarry_combo.count()):
            if self._quarry_combo.itemData(i) == quarry.id:
                if i != self._quarry_combo.currentIndex():
                    self._quarry_combo.blockSignals(True)
                    self._quarry_combo.setCurrentIndex(i)
                    self._quarry_combo.blockSignals(False)
                    self._load_quarry_data(quarry)  # type: ignore[arg-type]
                return
        self.refresh()  # quarry not in the combo yet (created elsewhere) — reload the list

    def _load_quarry_data(self, quarry: Quarry) -> None:
        def load() -> tuple[int, list[Report], AnalysisResult | None]:
            sections = self._api.list_sections(quarry.id)
            reports = self._api.list_reports(quarry.id)
            latest: AnalysisResult | None = None
            if reports:
                latest = self._api.get_analysis_result(reports[0].analysis_result_id)
            return len(sections), reports, latest

        submit(load, self._on_quarry_data, self._on_error)

    # --- Rendering ---------------------------------------------------------------------

    def _on_quarry_data(self, data: tuple[int, list[Report], AnalysisResult | None]) -> None:
        n_sections, reports, latest = data
        self._card_sections.set_value(str(n_sections))
        self._card_reports.set_value(str(len(reports)))
        self._card_p80.set_value(
            f"{latest.p80_mm:g} мм" if latest and latest.p80_mm is not None else "—"
        )
        self._histogram.set_bins(latest.size_distribution or [] if latest else [])

        self._reports_list.clear()
        for report in reports[:6]:
            badge = "⚠ mock" if report.analysis_method == "mock" else "real"
            date = report.created_at[:10]
            item = QListWidgetItem(f"{report.title}\n{date} · {badge}")
            if report.analysis_method == "mock":
                item.setToolTip("⚠ Mock pipeline — результаты синтетические")
            self._reports_list.addItem(item)

    def _show_empty(self) -> None:
        self._card_sections.set_value("—")
        self._card_reports.set_value("—")
        self._card_p80.set_value("—")
        self._histogram.set_bins([])
        self._reports_list.clear()

    def _on_error(self, message: str) -> None:
        self._error_label.setText(message)
