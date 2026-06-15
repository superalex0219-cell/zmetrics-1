"""Small UI layout helpers shared by desktop screens."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QFormLayout, QLabel, QLayout, QSizePolicy


_DIALOG_STYLESHEET = """
QDialog {
    background: #f5f7fa;
    color: #203040;
}
QDialog QLabel {
    background: transparent;
    color: #203040;
}
QDialog QLineEdit,
QDialog QComboBox,
QDialog QTextEdit,
QDialog QPlainTextEdit {
    background: #ffffff;
    border: 1px solid #c8d2df;
    border-radius: 5px;
    color: #203040;
    min-height: 28px;
    padding: 3px 8px;
}
QDialog QLineEdit:focus,
QDialog QComboBox:focus,
QDialog QTextEdit:focus,
QDialog QPlainTextEdit:focus {
    border-color: #2f80ed;
}
QDialog QPushButton {
    background: #ffffff;
    border: 1px solid #c8d2df;
    border-radius: 5px;
    color: #243447;
    min-height: 28px;
    min-width: 72px;
    padding: 5px 12px;
}
QDialog QPushButton:hover {
    background: #f1f6fb;
    border-color: #9bb4cf;
}
QDialog QPushButton:pressed {
    background: #e5eef8;
}
QDialog QPushButton:default {
    border-color: #2f80ed;
}
"""


def apply_screen_layout(layout: QLayout) -> None:
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(12)


def apply_dialog_theme(dialog: QDialog) -> None:
    dialog.setStyleSheet(_DIALOG_STYLESHEET)


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
