"""Site sections screen: sections of the selected quarry + create form.

The quarry selector is synced with ``AppState`` in both directions (combo change →
``set_quarry``; external ``quarry_changed`` → combo follows). Создание участка требует
роль blaster на карьере — 403 от сервера показывается в форме.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
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
from zmetrics_desktop.models import Quarry, SiteSection
from zmetrics_desktop.ui.layout import (
    apply_form_layout,
    apply_screen_layout,
    configure_combo,
    configure_error_label,
)
from zmetrics_desktop.ui.state import ROLE_BLASTER
from zmetrics_desktop.ui.workers import submit

if TYPE_CHECKING:
    from zmetrics_desktop.context import AppContext
    from zmetrics_desktop.ui.state import AppState


class SectionsScreen(QWidget):
    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._api = ZMetricsApi(context.api)
        self._state = state
        self._loaded_once = False
        self._quarries: list[Quarry] = []
        self._sections: list[SiteSection] = []

        root = QVBoxLayout(self)
        apply_screen_layout(root)

        header = QHBoxLayout()
        header.addWidget(QLabel("Карьер:"))
        self._quarry_combo = QComboBox()
        configure_combo(self._quarry_combo)
        self._quarry_combo.currentIndexChanged.connect(self._on_quarry_selected)
        header.addWidget(self._quarry_combo, stretch=1)
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.refresh)
        header.addWidget(refresh)
        self._edit_button = QPushButton("Изменить выбранный…")
        self._edit_button.setVisible(False)  # fail closed: нужна роль blaster
        self._edit_button.clicked.connect(self._open_edit_dialog)
        header.addWidget(self._edit_button)
        header.addStretch(1)
        root.addLayout(header)

        self._error_label = QLabel()
        configure_error_label(self._error_label)
        root.addWidget(self._error_label)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Название", "№ блока", "Описание"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.itemSelectionChanged.connect(self._update_edit_button)
        root.addWidget(self._table, stretch=1)

        root.addWidget(self._build_create_form())

        self._state.quarry_changed.connect(self._on_state_quarry_changed)
        self._state.access_changed.connect(self._update_edit_button)

    def _build_create_form(self) -> QGroupBox:
        box = QGroupBox("Новый участок / блок")
        form = QFormLayout(box)
        apply_form_layout(form)
        self._name_edit = QLineEdit()
        self._block_edit = QLineEdit()
        self._description_edit = QLineEdit()
        form.addRow("Название*:", self._name_edit)
        form.addRow("№ блока:", self._block_edit)
        form.addRow("Описание:", self._description_edit)

        buttons = QHBoxLayout()
        self._create_button = QPushButton("Создать")
        self._create_button.clicked.connect(self._create)
        buttons.addWidget(self._create_button)
        buttons.addStretch(1)
        form.addRow(buttons)
        self._form_error = QLabel()
        configure_error_label(self._form_error)
        form.addRow(self._form_error)
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
            self._load_sections(quarries[index])
        else:
            self._state.set_quarry(None)
            self._render_sections([])

    def _on_quarry_selected(self, index: int) -> None:
        if 0 <= index < len(self._quarries):
            quarry = self._quarries[index]
            self._state.set_quarry(quarry)
            self._load_sections(quarry)

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
                    self._load_sections(quarry)  # type: ignore[arg-type]
                return
        self.refresh()  # quarry not in the combo yet (created elsewhere) — reload the list

    def _load_sections(self, quarry: Quarry) -> None:
        submit(
            lambda: self._api.list_sections(quarry.id),
            self._render_sections,
            self._error_label.setText,
        )

    def _render_sections(self, sections: list[SiteSection]) -> None:
        self._sections = sections
        self._table.setRowCount(len(sections))
        for row, section in enumerate(sections):
            cells = [section.name, section.block_number or "", section.description or ""]
            for col, text in enumerate(cells):
                self._table.setItem(row, col, QTableWidgetItem(text))

    # --- Editing (EDIT-1) -----------------------------------------------------------

    def _selected_section(self) -> SiteSection | None:
        rows = {item.row() for item in self._table.selectedItems()}
        if len(rows) == 1:
            row = rows.pop()
            if 0 <= row < len(self._sections):
                return self._sections[row]
        return None

    def _update_edit_button(self, *_: object) -> None:
        quarry = self._state.quarry
        self._edit_button.setVisible(
            self._selected_section() is not None
            and quarry is not None
            and self._state.role_level(quarry.id) >= ROLE_BLASTER
        )

    def _open_edit_dialog(self) -> None:
        section = self._selected_section()
        quarry = self._state.quarry
        if section is None or quarry is None:
            return
        from zmetrics_desktop.ui.edit_dialogs import EditFormDialog

        dialog = EditFormDialog("Изменить участок", [
            ("name", "Название:", section.name, "str"),
            ("block_number", "№ блока:", section.block_number, "str"),
            ("description", "Описание:", section.description, "str"),
        ], self)
        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.changes:
            return
        changes = dialog.changes
        submit(
            lambda: self._api.update_section(quarry.id, section.id, changes),
            lambda _s: self._load_sections(quarry),
            self._error_label.setText,
        )

    # --- Creation -----------------------------------------------------------------

    def _create(self) -> None:
        self._form_error.clear()
        quarry = self._state.quarry
        if quarry is None:
            self._form_error.setText("Сначала выберите карьер")
            return
        name = self._name_edit.text().strip()
        if not name:
            self._form_error.setText("Укажите название")
            return
        body = {
            "name": name,
            "block_number": self._block_edit.text().strip() or None,
            "description": self._description_edit.text().strip() or None,
        }

        self._create_button.setEnabled(False)
        submit(
            lambda: self._api.create_section(quarry.id, body),
            self._on_created,
            self._on_create_error,
        )

    def _on_created(self, section: SiteSection) -> None:
        self._create_button.setEnabled(True)
        for edit in (self._name_edit, self._block_edit, self._description_edit):
            edit.clear()
        if self._state.quarry is not None:
            self._load_sections(self._state.quarry)

    def _on_create_error(self, message: str) -> None:
        self._create_button.setEnabled(True)
        self._form_error.setText(message)
