"""Blast passport screen: list, detail, create, explicit status transitions, blast event.

SAFETY: every transition (submit/approve/activate/complete) and the blast-event creation
happens ONLY on a button click followed by a confirmation dialog — никаких автоматических
переходов. Кнопки гейтятся ролью из ``AppState`` (``/access``); сервер всё равно
перепроверяет роль и статус на каждом вызове. Поля нового паспорта пользователь вводит
вручную — никакого префилла из рекомендаций.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from zmetrics_desktop.api.client import ApiError
from zmetrics_desktop.api.zmetrics import ZMetricsApi
from zmetrics_desktop.models import BlastEvent, BlastPassport, Quarry, SiteSection
from zmetrics_desktop.ui.quarries import optional_float
from zmetrics_desktop.ui.state import ROLE_ADMIN, ROLE_BLASTER
from zmetrics_desktop.ui.workers import submit

if TYPE_CHECKING:
    from zmetrics_desktop.context import AppContext
    from zmetrics_desktop.ui.state import AppState

STATUS_RU = {
    "draft": "Черновик",
    "submitted": "На утверждении",
    "approved": "Утверждён",
    "active": "Активен",
    "completed": "Завершён",
    "cancelled": "Отменён",
    "superseded": "Заменён ревизией",
}

# (action, button label, confirmation text, required current status, required role)
TRANSITIONS: list[tuple[str, str, str, str, int]] = [
    ("submit", "Отправить на утверждение",
     "Отправить паспорт на утверждение?", "draft", ROLE_BLASTER),
    ("approve", "Утвердить",
     "Утвердить паспорт БВР? Действие фиксируется в журнале аудита.", "submitted", ROLE_ADMIN),
    ("activate", "Активировать",
     "Активировать паспорт (разрешить взрывные работы)?", "approved", ROLE_ADMIN),
    ("complete", "Завершить",
     "Завершить паспорт (работы выполнены)?", "active", ROLE_ADMIN),
]


def _fmt(value: object, suffix: str = "") -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, float):
        return f"{value:g}{suffix}"
    return f"{value}{suffix}"


class PassportCreateDialog(QDialog):
    """Новый паспорт: все параметры вводятся вручную (без префилла из рекомендаций)."""

    def __init__(self, sections: list[SiteSection], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Новый паспорт БВР")
        self._sections = sections
        form = QFormLayout(self)

        self._section_combo = QComboBox()
        for section in sections:
            self._section_combo.addItem(section.name, section.id)
        form.addRow("Участок*:", self._section_combo)

        self._edits: dict[str, QLineEdit] = {}
        for key, label in [
            ("blast_date_planned", "Дата взрыва (план, ГГГГ-ММ-ДД):"),
            ("explosive_type", "Тип ВВ:"),
            ("total_explosive_kg", "Общий заряд, кг:"),
            ("number_of_holes", "Кол-во скважин:"),
            ("hole_diameter_mm", "Диаметр скважины, мм:"),
            ("hole_depth_m", "Глубина скважины, м:"),
            ("burden_m", "ЛНС (burden), м:"),
            ("spacing_m", "Расстояние в ряду (spacing), м:"),
            ("stemming_m", "Забойка (stemming), м:"),
            ("target_p80_mm", "Целевой P80, мм:"),
            ("notes", "Примечания:"),
        ]:
            edit = QLineEdit()
            self._edits[key] = edit
            form.addRow(label, edit)

        self._error = QLabel()
        self._error.setStyleSheet("color: #b00;")
        form.addRow(self._error)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        self.body: dict | None = None

    def _validate_and_accept(self) -> None:
        self._error.clear()
        if self._section_combo.currentIndex() < 0:
            self._error.setText("Выберите участок")
            return
        body: dict = {"site_section_id": self._section_combo.currentData()}
        try:
            for key in ("total_explosive_kg", "hole_diameter_mm", "hole_depth_m",
                        "burden_m", "spacing_m", "stemming_m", "target_p80_mm"):
                body[key] = optional_float(self._edits[key].text())
        except ValueError as exc:
            self._error.setText(str(exc))
            return
        holes = self._edits["number_of_holes"].text().strip()
        if holes:
            if not holes.isdigit():
                self._error.setText(f"Кол-во скважин — целое число, не «{holes}»")
                return
            body["number_of_holes"] = int(holes)
        for key in ("blast_date_planned", "explosive_type", "notes"):
            body[key] = self._edits[key].text().strip() or None
        self.body = body
        self.accept()


class BlastEventDialog(QDialog):
    """Фиксация фактического взрыва по утверждённому/активному паспорту."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Зафиксировать взрыв")
        form = QFormLayout(self)

        self._datetime_edit = QLineEdit(datetime.now().isoformat(timespec="minutes"))
        self._explosive_edit = QLineEdit()
        self._weather_edit = QLineEdit()
        self._notes_edit = QLineEdit()
        form.addRow("Дата и время*:", self._datetime_edit)
        form.addRow("Фактический заряд, кг:", self._explosive_edit)
        form.addRow("Погодные условия:", self._weather_edit)
        form.addRow("Примечания:", self._notes_edit)

        self._error = QLabel()
        self._error.setStyleSheet("color: #b00;")
        form.addRow(self._error)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        self.body: dict | None = None

    def _validate_and_accept(self) -> None:
        self._error.clear()
        raw = self._datetime_edit.text().strip()
        try:
            datetime.fromisoformat(raw)
        except ValueError:
            self._error.setText("Формат: ГГГГ-ММ-ДДTЧЧ:ММ")
            return
        try:
            explosive = optional_float(self._explosive_edit.text())
        except ValueError as exc:
            self._error.setText(str(exc))
            return
        self.body = {
            "blast_datetime": raw,
            "actual_explosive_kg": explosive,
            "weather_conditions": self._weather_edit.text().strip() or None,
            "notes": self._notes_edit.text().strip() or None,
        }
        self.accept()


class PassportsScreen(QWidget):
    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._api = ZMetricsApi(context.api)
        self._state = state
        self._loaded_once = False
        self._quarries: list[Quarry] = []
        self._sections: list[SiteSection] = []
        self._passports: list[BlastPassport] = []
        self._selected: BlastPassport | None = None
        self._blast_event: BlastEvent | None = None

        root = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addWidget(QLabel("Карьер:"))
        self._quarry_combo = QComboBox()
        self._quarry_combo.setMinimumWidth(280)
        self._quarry_combo.currentIndexChanged.connect(self._on_quarry_selected)
        header.addWidget(self._quarry_combo)
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.refresh)
        header.addWidget(refresh)
        self._create_button = QPushButton("Создать паспорт…")
        self._create_button.clicked.connect(self._open_create_dialog)
        self._create_button.setVisible(False)  # fail closed until /access is known
        header.addWidget(self._create_button)
        header.addStretch(1)
        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: #b00;")
        header.addWidget(self._error_label)
        root.addLayout(header)

        splitter = QSplitter()
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Статус", "Рев.", "Участок", "Дата (план)", "P80 цель, мм"]
        )
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.itemSelectionChanged.connect(self._on_row_selected)
        splitter.addWidget(self._table)
        splitter.addWidget(self._build_detail_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, stretch=1)

        self._state.quarry_changed.connect(self._on_state_quarry_changed)
        self._state.access_changed.connect(self._apply_role_gating)
        self._apply_role_gating()  # access may already be loaded

    def _build_detail_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self._detail_box = QGroupBox("Паспорт")
        form = QFormLayout(self._detail_box)
        self._detail_labels: dict[str, QLabel] = {}
        for key, label in [
            ("status", "Статус:"),
            ("revision", "Ревизия:"),
            ("section", "Участок:"),
            ("blast_date_planned", "Дата взрыва (план):"),
            ("explosive_type", "Тип ВВ:"),
            ("total_explosive_kg", "Общий заряд:"),
            ("number_of_holes", "Скважин:"),
            ("hole_diameter_mm", "Диаметр:"),
            ("hole_depth_m", "Глубина:"),
            ("burden_m", "ЛНС (burden):"),
            ("spacing_m", "Расст. в ряду (spacing):"),
            ("stemming_m", "Забойка (stemming):"),
            ("target_p80_mm", "Целевой P80:"),
            ("notes", "Примечания:"),
            ("blast_event", "Взрыв:"),
        ]:
            value = QLabel("—")
            value.setWordWrap(True)
            self._detail_labels[key] = value
            form.addRow(label, value)

        buttons = QHBoxLayout()
        self._transition_buttons: dict[str, QPushButton] = {}
        for action, label, confirmation, _required_status, _required_role in TRANSITIONS:
            button = QPushButton(label)
            button.setVisible(False)
            button.clicked.connect(
                lambda _=False, a=action, c=confirmation: self._confirm_transition(a, c)
            )
            self._transition_buttons[action] = button
            buttons.addWidget(button)
        self._blast_button = QPushButton("Зафиксировать взрыв…")
        self._blast_button.setVisible(False)
        self._blast_button.clicked.connect(self._open_blast_dialog)
        buttons.addWidget(self._blast_button)
        buttons.addStretch(1)

        self._action_error = QLabel()
        self._action_error.setStyleSheet("color: #b00;")
        self._action_error.setWordWrap(True)

        layout.addWidget(self._detail_box)
        layout.addLayout(buttons)
        layout.addWidget(self._action_error)
        layout.addStretch(1)
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
            self._load_quarry_data(quarries[index])
        else:
            self._state.set_quarry(None)
            self._render_passports([], [])
        self._apply_role_gating()

    def _on_quarry_selected(self, index: int) -> None:
        if 0 <= index < len(self._quarries):
            quarry = self._quarries[index]
            self._state.set_quarry(quarry)
            self._load_quarry_data(quarry)
            self._apply_role_gating()

    def _on_state_quarry_changed(self, quarry: object) -> None:
        if quarry is None or not self._loaded_once:
            return
        for i in range(self._quarry_combo.count()):
            if self._quarry_combo.itemData(i) == quarry.id:
                if i != self._quarry_combo.currentIndex():
                    self._quarry_combo.blockSignals(True)
                    self._quarry_combo.setCurrentIndex(i)
                    self._quarry_combo.blockSignals(False)
                    self._load_quarry_data(quarry)  # type: ignore[arg-type]
                    self._apply_role_gating()
                return
        self.refresh()

    def _load_quarry_data(self, quarry: Quarry) -> None:
        def load() -> tuple[list[SiteSection], list[BlastPassport]]:
            return self._api.list_sections(quarry.id), self._api.list_passports(quarry.id)

        submit(lambda: load(), self._on_quarry_data, self._error_label.setText)

    def _on_quarry_data(self, data: tuple[list[SiteSection], list[BlastPassport]]) -> None:
        sections, passports = data
        self._render_passports(sections, passports)

    def _render_passports(
        self, sections: list[SiteSection], passports: list[BlastPassport]
    ) -> None:
        self._sections = sections
        self._passports = passports
        section_names = {s.id: s.name for s in sections}

        selected_id = self._selected.id if self._selected else None
        self._table.blockSignals(True)
        self._table.setRowCount(len(passports))
        for row, passport in enumerate(passports):
            cells = [
                STATUS_RU.get(passport.status, passport.status),
                str(passport.revision_number),
                section_names.get(passport.site_section_id, "?"),
                (passport.blast_date_planned or "")[:10],
                _fmt(passport.target_p80_mm),
            ]
            for col, text in enumerate(cells):
                self._table.setItem(row, col, QTableWidgetItem(text))
        self._table.blockSignals(False)

        self._selected = None
        self._blast_event = None
        for row, passport in enumerate(passports):
            if passport.id == selected_id:
                self._table.selectRow(row)  # re-renders the detail via the signal
                break
        if self._selected is None:
            self._render_detail(None)

    # --- Detail -------------------------------------------------------------------

    def _on_row_selected(self) -> None:
        rows = {item.row() for item in self._table.selectedItems()}
        if len(rows) != 1:
            return
        row = rows.pop()
        if not (0 <= row < len(self._passports)):
            return
        self._selected = self._passports[row]
        self._blast_event = None
        self._render_detail(self._selected)
        self._load_blast_event(self._selected)

    def _load_blast_event(self, passport: BlastPassport) -> None:
        quarry = self._state.quarry
        if quarry is None:
            return

        def load() -> BlastEvent | None:
            try:
                return self._api.get_blast_event(quarry.id, passport.id)
            except ApiError as exc:
                if exc.status_code == 404:  # взрыва ещё не было — это норма
                    return None
                raise

        submit(load, lambda event, p=passport: self._on_blast_event(p, event),
               self._error_label.setText)

    def _on_blast_event(self, passport: BlastPassport, event: object) -> None:
        if self._selected is None or self._selected.id != passport.id:
            return  # selection moved on while loading
        self._blast_event = event  # type: ignore[assignment]
        self._render_detail(self._selected)

    def _render_detail(self, passport: BlastPassport | None) -> None:
        self._action_error.clear()
        labels = self._detail_labels
        if passport is None:
            for value in labels.values():
                value.setText("—")
            for button in self._transition_buttons.values():
                button.setVisible(False)
            self._blast_button.setVisible(False)
            return

        section_names = {s.id: s.name for s in self._sections}
        labels["status"].setText(STATUS_RU.get(passport.status, passport.status))
        labels["revision"].setText(str(passport.revision_number))
        labels["section"].setText(section_names.get(passport.site_section_id, "?"))
        labels["blast_date_planned"].setText(_fmt((passport.blast_date_planned or "")[:10]))
        labels["explosive_type"].setText(_fmt(passport.explosive_type))
        labels["total_explosive_kg"].setText(_fmt(passport.total_explosive_kg, " кг"))
        labels["number_of_holes"].setText(_fmt(passport.number_of_holes))
        labels["hole_diameter_mm"].setText(_fmt(passport.hole_diameter_mm, " мм"))
        labels["hole_depth_m"].setText(_fmt(passport.hole_depth_m, " м"))
        labels["burden_m"].setText(_fmt(passport.burden_m, " м"))
        labels["spacing_m"].setText(_fmt(passport.spacing_m, " м"))
        labels["stemming_m"].setText(_fmt(passport.stemming_m, " м"))
        labels["target_p80_mm"].setText(_fmt(passport.target_p80_mm, " мм"))
        labels["notes"].setText(_fmt(passport.notes))
        if self._blast_event is not None:
            event = self._blast_event
            labels["blast_event"].setText(
                f"{event.blast_datetime[:16].replace('T', ' ')}"
                f" · факт. заряд: {_fmt(event.actual_explosive_kg, ' кг')}"
            )
        else:
            labels["blast_event"].setText("не зафиксирован")

        role = self._state.role_level(self._state.quarry.id if self._state.quarry else None)
        for action, _label, _confirmation, required_status, required_role in TRANSITIONS:
            self._transition_buttons[action].setVisible(
                passport.status == required_status and role >= required_role
            )
        self._blast_button.setVisible(
            passport.status in ("approved", "active")
            and role >= ROLE_BLASTER
            and self._blast_event is None
        )

    def _apply_role_gating(self) -> None:
        quarry_id = self._state.quarry.id if self._state.quarry else None
        self._create_button.setVisible(
            self._state.role_level(quarry_id) >= ROLE_BLASTER
        )
        if self._selected is not None:
            self._render_detail(self._selected)

    # --- Actions (explicit, confirmed) ----------------------------------------------

    def _confirm_transition(self, action: str, confirmation: str) -> None:
        """SAFETY: transition runs only after an explicit click + confirmation."""
        passport = self._selected
        quarry = self._state.quarry
        if passport is None or quarry is None:
            return
        answer = QMessageBox.question(
            self, "Подтверждение", confirmation,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._action_error.clear()
        submit(
            lambda: self._api.transition_passport(quarry.id, passport.id, action),
            self._on_transition_done,
            self._action_error.setText,
        )

    def _on_transition_done(self, passport: BlastPassport) -> None:
        self._selected = passport
        if self._state.quarry is not None:
            self._load_quarry_data(self._state.quarry)

    def _open_create_dialog(self) -> None:
        if not self._sections:
            self._error_label.setText("Сначала создайте участок на экране «Участки»")
            return
        dialog = PassportCreateDialog(self._sections, self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.body is None:
            return
        quarry = self._state.quarry
        if quarry is None:
            return
        body = dialog.body
        submit(
            lambda: self._api.create_passport(quarry.id, body),
            self._on_transition_done,  # select the new passport + reload the list
            self._error_label.setText,
        )

    def _open_blast_dialog(self) -> None:
        passport = self._selected
        quarry = self._state.quarry
        if passport is None or quarry is None:
            return
        dialog = BlastEventDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.body is None:
            return
        body = dialog.body
        submit(
            lambda: self._api.create_blast_event(quarry.id, passport.id, body),
            lambda event, p=passport: self._on_blast_event(p, event),
            self._action_error.setText,
        )
