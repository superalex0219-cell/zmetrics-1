"""Small UI layout helpers shared by desktop screens."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QLayout, QSizePolicy


def apply_screen_layout(layout: QLayout) -> None:
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(12)


def apply_form_layout(form: QFormLayout) -> None:
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
    form.setHorizontalSpacing(12)
    form.setVerticalSpacing(8)


def configure_wrapping_label(label: QLabel) -> None:
    label.setWordWrap(True)
    label.setMinimumWidth(0)
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)


def configure_error_label(label: QLabel) -> None:
    label.setStyleSheet("color: #9f2a1d;")
    configure_wrapping_label(label)


def configure_combo(combo: QComboBox, minimum_width: int = 160) -> None:
    combo.setMinimumWidth(minimum_width)
    combo.setSizePolicy(
        QSizePolicy.Policy.MinimumExpanding,
        QSizePolicy.Policy.Fixed,
    )
