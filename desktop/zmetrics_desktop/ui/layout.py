"""Small UI layout helpers shared by desktop screens."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLabel, QLayout, QSizePolicy


def apply_screen_layout(layout: QLayout) -> None:
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(12)


def configure_error_label(label: QLabel) -> None:
    label.setStyleSheet("color: #9f2a1d;")
    label.setWordWrap(True)
    label.setMinimumWidth(0)
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)


def configure_combo(combo: QComboBox, minimum_width: int = 160) -> None:
    combo.setMinimumWidth(minimum_width)
    combo.setSizePolicy(
        QSizePolicy.Policy.MinimumExpanding,
        QSizePolicy.Policy.Fixed,
    )
