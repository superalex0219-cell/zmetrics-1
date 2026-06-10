"""Shared chart widgets (no charting dependency — plain QPainter)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from zmetrics_desktop.models import SizeBin


class HistogramWidget(QWidget):
    """Bar chart of the cumulative size distribution (размер, мм → % прохождения)."""

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
