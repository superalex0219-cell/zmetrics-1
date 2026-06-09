"""Dashboard screen: quarry selector, metric cards, P80, fraction histogram, recent
reports. Parity with the former web dashboard (counters + size distribution + latest
reports with the mock/real badge)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from zmetrics_desktop.api.zmetrics import ZMetricsApi
from zmetrics_desktop.models import AnalysisResult, Quarry, Report, SizeBin
from zmetrics_desktop.ui.workers import submit

if TYPE_CHECKING:
    from zmetrics_desktop.context import AppContext
    from zmetrics_desktop.ui.state import AppState


class _MetricCard(QFrame):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(self)
        self._value = QLabel("—")
        self._value.setStyleSheet("font-size: 24px; font-weight: 600;")
        caption = QLabel(label)
        caption.setStyleSheet("color: gray;")
        layout.addWidget(self._value)
        layout.addWidget(caption)

    def set_value(self, value: str) -> None:
        self._value.setText(value)


class _HistogramWidget(QWidget):
    """Bar chart of the cumulative size distribution (no charting dependency)."""

    def __init__(self) -> None:
        super().__init__()
        self._bins: list[SizeBin] = []
        self.setMinimumHeight(220)

    def set_bins(self, bins: list[SizeBin]) -> None:
        self._bins = bins
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 — Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(8, 8, -8, -24)

        if not self._bins:
            painter.setPen(QPen(QColor("gray")))
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter,
                "Нет данных анализа.\nЗапустите анализ на экране «Съёмка».",
            )
            return

        bar_color = self.palette().highlight().color()
        text_pen = QPen(self.palette().text().color())
        n = len(self._bins)
        slot = rect.width() / n
        bar_w = max(6.0, slot * 0.6)

        for i, size_bin in enumerate(self._bins):
            pct = max(0.0, min(100.0, size_bin.cumulative_passing_pct))
            bar_h = rect.height() * pct / 100.0
            x = rect.left() + i * slot + (slot - bar_w) / 2
            y = rect.bottom() - bar_h
            painter.fillRect(int(x), int(y), int(bar_w), int(bar_h), bar_color)

            painter.setPen(text_pen)
            label = f"{size_bin.size_mm:g}"
            painter.drawText(
                int(rect.left() + i * slot), rect.bottom() + 4, int(slot), 16,
                Qt.AlignmentFlag.AlignHCenter, label,
            )
        painter.setPen(QPen(QColor("gray")))
        painter.drawText(self.rect().adjusted(8, 0, -8, -2),
                         Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
                         "размер, мм → % прохождения")


class DashboardScreen(QWidget):
    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._api = ZMetricsApi(context.api)
        self._state = state
        self._loaded_once = False
        self._quarries: list[Quarry] = []

        root = QVBoxLayout(self)

        # Header: quarry selector + refresh
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

        # Metric cards
        cards = QHBoxLayout()
        self._card_quarries = _MetricCard("Карьеры")
        self._card_sections = _MetricCard("Участки")
        self._card_reports = _MetricCard("Отчёты")
        self._card_p80 = _MetricCard("P80 (последний анализ)")
        for card in (self._card_quarries, self._card_sections, self._card_reports, self._card_p80):
            cards.addWidget(card)
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
        hist_holder.setLayout(hist_box)
        reports_holder.setLayout(reports_box)
        body.addWidget(hist_holder, 0, 0)
        body.addWidget(reports_holder, 0, 1)
        body.setColumnStretch(0, 3)
        body.setColumnStretch(1, 2)
        root.addLayout(body, stretch=1)

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
