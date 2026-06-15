"""EDIT-1: универсальный диалог редактирования полей сущности.

Поля описываются кортежами ``(key, label, initial, kind)``, где ``kind`` —
``"str" | "float" | "int"``. После OK ``changes`` содержит только изменённые
поля (PATCH-семантика); пустое значение → ``None``.

SAFETY: диалог никогда не префиллится из рекомендаций — только из текущих
значений самой сущности.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QWidget,
)

from zmetrics_desktop.ui.layout import apply_form_layout, configure_error_label
from zmetrics_desktop.ui.quarries import optional_float

FieldSpec = tuple[str, str, object, str]  # (key, label, initial, kind)


class EditFormDialog(QDialog):
    def __init__(
        self,
        title: str,
        fields: list[FieldSpec],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self._fields = fields
        self._initial: dict[str, object] = {}
        self._edits: dict[str, QLineEdit] = {}
        self.changes: dict | None = None

        form = QFormLayout(self)
        apply_form_layout(form)
        for key, label, initial, _kind in fields:
            text = "" if initial is None else (
                f"{initial:g}" if isinstance(initial, float) else str(initial)
            )
            edit = QLineEdit(text)
            self._edits[key] = edit
            self._initial[key] = initial
            form.addRow(label, edit)

        self._error = QLabel()
        configure_error_label(self._error)
        form.addRow(self._error)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Сохранить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _validate_and_accept(self) -> None:
        self._error.clear()
        changes: dict = {}
        for key, _label, _initial, kind in self._fields:
            raw = self._edits[key].text().strip()
            value: object
            if kind == "float":
                try:
                    value = optional_float(raw)
                except ValueError as exc:
                    self._error.setText(str(exc))
                    return
            elif kind == "int":
                if raw and not raw.isdigit():
                    self._error.setText(f"Целое число, не «{raw}»")
                    return
                value = int(raw) if raw else None
            else:
                value = raw or None
            if value != self._initial[key]:
                changes[key] = value
        self.changes = changes
        self.accept()
