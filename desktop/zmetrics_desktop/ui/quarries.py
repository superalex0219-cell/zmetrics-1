"""Quarries screen: list of accessible quarries + create form.

Backend rule: создать карьер может admin любого карьера (или кто угодно, пока карьеров
нет вообще — bootstrap). 403 от сервера показывается как есть; UI-гейтинг кнопок
появится вместе с `/access` на экране паспортов.

Selecting a row publishes the quarry to ``AppState`` so the other screens follow.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtWidgets import QDialog

from zmetrics_desktop.api.zmetrics import ZMetricsApi
from zmetrics_desktop.models import Quarry
from zmetrics_desktop.ui.layout import apply_screen_layout, configure_error_label
from zmetrics_desktop.ui.state import ROLE_ADMIN
from zmetrics_desktop.ui.workers import submit

if TYPE_CHECKING:
    from zmetrics_desktop.context import AppContext
    from zmetrics_desktop.ui.state import AppState


def optional_float(text: str) -> float | None:
    """Parse a coordinate field: empty → None; comma accepted as decimal separator.

    Raises ``ValueError`` with a Russian message for the form error label.
    """
    text = text.strip()
    if not text:
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        raise ValueError(f"Не число: «{text}»") from None


class QuarriesScreen(QWidget):
    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._api = ZMetricsApi(context.api)
        self._state = state
        self._loaded_once = False
        self._quarries: list[Quarry] = []

        root = QVBoxLayout(self)
        apply_screen_layout(root)

        header = QHBoxLayout()
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.refresh)
        header.addWidget(refresh)
        self._edit_button = QPushButton("Изменить выбранный…")
        self._edit_button.setVisible(False)  # fail closed: нужна роль admin на карьере
        self._edit_button.clicked.connect(self._open_edit_dialog)
        header.addWidget(self._edit_button)
        self._error_label = QLabel()
        configure_error_label(self._error_label)
        header.addWidget(self._error_label, stretch=1)
        root.addLayout(header)

        state.access_changed.connect(self._update_edit_button)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Название", "Расположение", "Широта", "Долгота"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.itemSelectionChanged.connect(self._on_row_selected)
        root.addWidget(self._table, stretch=1)

        root.addWidget(self._build_create_form())

    def _build_create_form(self) -> QGroupBox:
        box = QGroupBox("Новый карьер")
        form = QFormLayout(box)
        self._name_edit = QLineEdit()
        self._location_edit = QLineEdit()
        self._lat_edit = QLineEdit()
        self._lat_edit.setPlaceholderText("например 55.16")
        self._lon_edit = QLineEdit()
        self._lon_edit.setPlaceholderText("например 61.40")
        form.addRow("Название*:", self._name_edit)
        form.addRow("Расположение:", self._location_edit)
        form.addRow("Широта:", self._lat_edit)
        form.addRow("Долгота:", self._lon_edit)

        buttons = QHBoxLayout()
        self._create_button = QPushButton("Создать")
        self._create_button.clicked.connect(self._create)
        buttons.addWidget(self._create_button)
        self._form_error = QLabel()
        configure_error_label(self._form_error)
        buttons.addWidget(self._form_error, stretch=1)
        form.addRow(buttons)
        return box

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
        self._table.blockSignals(True)
        self._table.setRowCount(len(quarries))
        for row, quarry in enumerate(quarries):
            cells = [
                quarry.name,
                quarry.location_description or "",
                f"{quarry.latitude:g}" if quarry.latitude is not None else "",
                f"{quarry.longitude:g}" if quarry.longitude is not None else "",
            ]
            for col, text in enumerate(cells):
                self._table.setItem(row, col, QTableWidgetItem(text))
        self._table.blockSignals(False)

        if self._state.quarry is not None:
            for row, quarry in enumerate(quarries):
                if quarry.id == self._state.quarry.id:
                    self._table.selectRow(row)
                    break

    def _on_row_selected(self) -> None:
        rows = {item.row() for item in self._table.selectedItems()}
        if len(rows) == 1:
            row = rows.pop()
            if 0 <= row < len(self._quarries):
                self._state.set_quarry(self._quarries[row])
        self._update_edit_button()

    # --- Editing (EDIT-1) -----------------------------------------------------------

    def _selected_quarry(self) -> Quarry | None:
        rows = {item.row() for item in self._table.selectedItems()}
        if len(rows) == 1:
            row = rows.pop()
            if 0 <= row < len(self._quarries):
                return self._quarries[row]
        return None

    def _update_edit_button(self, *_: object) -> None:
        quarry = self._selected_quarry()
        self._edit_button.setVisible(
            quarry is not None and self._state.role_level(quarry.id) >= ROLE_ADMIN
        )

    def _open_edit_dialog(self) -> None:
        quarry = self._selected_quarry()
        if quarry is None:
            return
        from zmetrics_desktop.ui.edit_dialogs import EditFormDialog

        dialog = EditFormDialog("Изменить карьер", [
            ("name", "Название:", quarry.name, "str"),
            ("location_description", "Расположение:", quarry.location_description, "str"),
            ("latitude", "Широта:", quarry.latitude, "float"),
            ("longitude", "Долгота:", quarry.longitude, "float"),
        ], self)
        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.changes:
            return
        changes = dialog.changes
        submit(
            lambda: self._api.update_quarry(quarry.id, changes),
            lambda _q: self.refresh(),
            self._error_label.setText,
        )

    # --- Creation -----------------------------------------------------------------

    def _create(self) -> None:
        self._form_error.clear()
        name = self._name_edit.text().strip()
        if not name:
            self._form_error.setText("Укажите название")
            return
        try:
            body = {
                "name": name,
                "location_description": self._location_edit.text().strip() or None,
                "latitude": optional_float(self._lat_edit.text()),
                "longitude": optional_float(self._lon_edit.text()),
            }
        except ValueError as exc:
            self._form_error.setText(str(exc))
            return

        self._create_button.setEnabled(False)
        submit(lambda: self._api.create_quarry(body), self._on_created, self._on_create_error)

    def _on_created(self, quarry: Quarry) -> None:
        self._create_button.setEnabled(True)
        for edit in (self._name_edit, self._location_edit, self._lat_edit, self._lon_edit):
            edit.clear()
        self._state.set_quarry(quarry)
        # Бэкенд выдал создателю admin на новый карьер — обновляем карту доступов,
        # иначе кнопки на новом карьере останутся выключенными до перезапуска.
        self._state.request_access_refresh()
        self.refresh()

    def _on_create_error(self, message: str) -> None:
        self._create_button.setEnabled(True)
        self._form_error.setText(message)
