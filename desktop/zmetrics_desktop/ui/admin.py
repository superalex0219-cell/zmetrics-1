"""Admin screen (ADMIN-USERS-2): пользователи, роли по карьерам, временные пароли.

Безопасность:
- временный пароль показывается РОВНО один раз: только в state экрана, копирование в
  буфер, «Скрыть» очищает; не пишется ни в логи, ни на диск;
- любые 403 показываются как «Недостаточно прав» без сырых ошибок;
- выдача/отзыв ролей — только явные действия, сервер пишет AuditLog.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
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

from zmetrics_desktop.api.zmetrics import ZMetricsApi
from zmetrics_desktop.models import AdminUser, Quarry, UserCreateResult, UserQuarryAccess
from zmetrics_desktop.ui.errors import human_error
from zmetrics_desktop.ui.layout import apply_screen_layout, configure_error_label
from zmetrics_desktop.ui.workers import submit

if TYPE_CHECKING:
    from zmetrics_desktop.context import AppContext
    from zmetrics_desktop.ui.state import AppState

ROLE_NAMES = ["user", "surveyor", "blaster", "admin"]


class UserEditDialog(QDialog):
    def __init__(self, user: AdminUser, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Редактировать пользователя")
        form = QFormLayout(self)
        self._full_name = QLineEdit(user.full_name)
        self._email = QLineEdit(user.email)
        form.addRow("ФИО:", self._full_name)
        form.addRow("Email:", self._email)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self._original = user

    @property
    def changes(self) -> dict:
        body: dict = {}
        if self._full_name.text().strip() != self._original.full_name:
            body["full_name"] = self._full_name.text().strip()
        if self._email.text().strip() != self._original.email:
            body["email"] = self._email.text().strip()
        return body


class UserCreateDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Создать пользователя")
        form = QFormLayout(self)
        self._email = QLineEdit()
        self._full_name = QLineEdit()
        form.addRow("Email*:", self._email)
        form.addRow("ФИО*:", self._full_name)
        self._error = QLabel()
        configure_error_label(self._error)
        form.addRow(self._error)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self.email: str | None = None
        self.full_name: str | None = None

    def _validate_and_accept(self) -> None:
        email = self._email.text().strip()
        full_name = self._full_name.text().strip()
        if not full_name:
            self._error.setText("Укажите ФИО")
            return
        # Keycloak требует ASCII-email (кириллица в адресе даёт 400 на сервере).
        if not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", email):
            self._error.setText("Некорректный email — латиницей, формата user@domain.tld")
            return
        self.email, self.full_name = email, full_name
        self.accept()


class AdminScreen(QWidget):
    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._api = ZMetricsApi(context.api)
        self._state = state
        self._loaded_once = False
        self._users: list[AdminUser] = []
        self._accesses: list[UserQuarryAccess] = []
        self._quarries: list[Quarry] = []
        self._selected: AdminUser | None = None

        root = QVBoxLayout(self)
        apply_screen_layout(root)

        header = QHBoxLayout()
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.refresh)
        header.addWidget(refresh)
        self._create_button = QPushButton("Создать пользователя…")
        self._create_button.clicked.connect(self._open_create_dialog)
        header.addWidget(self._create_button)
        self._error_label = QLabel()
        configure_error_label(self._error_label)
        header.addWidget(self._error_label, stretch=1)
        root.addLayout(header)

        # Temp-password box: только в памяти экрана, «Скрыть» очищает.
        self._password_box = QFrame()
        self._password_box.setFrameShape(QFrame.Shape.StyledPanel)
        self._password_box.setStyleSheet(
            "QFrame { background: #4a3a00; border: 1px solid #b06000; border-radius: 4px; }"
        )
        box_layout = QHBoxLayout(self._password_box)
        self._password_label = QLabel()
        # PlainText — пароль никогда не интерпретируется как разметка
        self._password_label.setTextFormat(Qt.TextFormat.PlainText)
        self._password_label.setStyleSheet("font-family: Consolas, monospace; color: #ffd54f;")
        self._password_label.setWordWrap(True)
        box_layout.addWidget(self._password_label, stretch=1)
        copy_button = QPushButton("Копировать")
        copy_button.clicked.connect(self._copy_password)
        box_layout.addWidget(copy_button)
        hide_button = QPushButton("Скрыть")
        hide_button.clicked.connect(self._clear_password)
        box_layout.addWidget(hide_button)
        self._password_box.setVisible(False)
        self._temp_password: str | None = None
        root.addWidget(self._password_box)

        splitter = QSplitter()

        users_panel = QWidget()
        users_panel.setMinimumWidth(0)
        users_layout = QVBoxLayout(users_panel)
        users_layout.addWidget(QLabel("Пользователи"))
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["ФИО", "Email", "Статус", "Создан"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.itemSelectionChanged.connect(self._on_row_selected)
        users_layout.addWidget(self._table, stretch=1)

        user_actions = QHBoxLayout()
        self._edit_button = QPushButton("Редактировать…")
        self._edit_button.clicked.connect(self._open_edit_dialog)
        self._reset_button = QPushButton("Сбросить пароль")
        self._reset_button.clicked.connect(self._reset_password)
        self._deactivate_button = QPushButton("Деактивировать")
        self._deactivate_button.clicked.connect(self._toggle_active)
        for button in (self._edit_button, self._reset_button, self._deactivate_button):
            button.setEnabled(False)
            user_actions.addWidget(button)
        user_actions.addStretch(1)
        users_layout.addLayout(user_actions)
        splitter.addWidget(users_panel)

        splitter.addWidget(self._build_roles_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, stretch=1)

    def _build_roles_panel(self) -> QWidget:
        panel = QGroupBox("Роли выбранного пользователя")
        panel.setMinimumWidth(0)
        layout = QVBoxLayout(panel)

        self._access_table = QTableWidget(0, 2)
        self._access_table.setHorizontalHeaderLabels(["Карьер", "Роль"])
        self._access_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._access_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._access_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._access_table, stretch=1)

        revoke_row = QHBoxLayout()
        self._revoke_button = QPushButton("Отозвать доступ")
        self._revoke_button.setEnabled(False)
        self._revoke_button.clicked.connect(self._revoke_access)
        revoke_row.addWidget(self._revoke_button)
        revoke_row.addStretch(1)
        layout.addLayout(revoke_row)
        self._access_table.itemSelectionChanged.connect(
            lambda: self._revoke_button.setEnabled(
                bool(self._access_table.selectedItems()) and self._selected is not None
            )
        )

        grant_box = QGroupBox("Назначить роль")
        grant_form = QFormLayout(grant_box)
        self._grant_quarry_combo = QComboBox()
        self._grant_role_combo = QComboBox()
        self._grant_role_combo.addItems(ROLE_NAMES)
        grant_form.addRow("Карьер:", self._grant_quarry_combo)
        grant_form.addRow("Роль:", self._grant_role_combo)
        self._grant_button = QPushButton("Назначить")
        self._grant_button.setEnabled(False)
        self._grant_button.clicked.connect(self._grant_access)
        grant_form.addRow(self._grant_button)
        layout.addWidget(grant_box)
        return panel

    # --- Loading ------------------------------------------------------------------

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 — Qt naming
        super().showEvent(event)
        if not self._loaded_once:
            self._loaded_once = True
            self.refresh()

    def refresh(self) -> None:
        self._error_label.clear()
        submit(self._api.admin_list_users, self._render_users, self._on_error)
        submit(self._api.list_quarries, self._on_quarries, self._on_error)

    def _on_error(self, message: str) -> None:
        self._error_label.setText(human_error(message))

    def _on_quarries(self, quarries: list[Quarry]) -> None:
        self._quarries = quarries
        self._grant_quarry_combo.clear()
        for quarry in quarries:
            self._grant_quarry_combo.addItem(quarry.name, quarry.id)

    def _render_users(self, users: list[AdminUser]) -> None:
        self._users = users
        selected_id = self._selected.id if self._selected else None
        self._table.blockSignals(True)
        self._table.setRowCount(len(users))
        for row, user in enumerate(users):
            cells = [
                user.full_name,
                user.email,
                "Активен" if user.is_active else "Отключён",
                user.created_at[:10],
            ]
            for col, text in enumerate(cells):
                self._table.setItem(row, col, QTableWidgetItem(text))
        self._table.blockSignals(False)

        self._selected = None
        for row, user in enumerate(users):
            if user.id == selected_id:
                self._table.selectRow(row)
                break
        if self._selected is None:
            self._render_accesses([])
            self._update_action_buttons()

    def _on_row_selected(self) -> None:
        rows = {item.row() for item in self._table.selectedItems()}
        if len(rows) != 1:
            return
        row = rows.pop()
        if not (0 <= row < len(self._users)):
            return
        self._selected = self._users[row]
        self._update_action_buttons()
        submit(
            lambda user_id=self._selected.id: self._api.admin_user_access(user_id),
            self._render_accesses,
            self._on_error,
        )

    def _update_action_buttons(self) -> None:
        user = self._selected
        enabled = user is not None
        self._edit_button.setEnabled(enabled)
        self._reset_button.setEnabled(enabled)
        self._deactivate_button.setEnabled(enabled)
        self._grant_button.setEnabled(enabled)
        if user is not None:
            self._deactivate_button.setText(
                "Деактивировать" if user.is_active else "Активировать"
            )

    def _render_accesses(self, accesses: list[UserQuarryAccess]) -> None:
        self._accesses = accesses
        self._access_table.setRowCount(len(accesses))
        for row, access in enumerate(accesses):
            self._access_table.setItem(row, 0, QTableWidgetItem(access.quarry_name))
            self._access_table.setItem(row, 1, QTableWidgetItem(access.role_name))
        self._revoke_button.setEnabled(False)

    # --- Temp password box ------------------------------------------------------------

    def _show_password(self, email: str, password: str) -> None:
        self._temp_password = password
        self._password_label.setText(
            f"⚠ Временный пароль для {email}:   {password}\n"
            "Передайте его пользователю безопасным способом. "
            "Пароль больше не будет показан."
        )
        self._password_box.setVisible(True)

    def _copy_password(self) -> None:
        if self._temp_password:
            QGuiApplication.clipboard().setText(self._temp_password)

    def _clear_password(self) -> None:
        self._temp_password = None
        self._password_label.clear()
        self._password_box.setVisible(False)

    # --- User actions -------------------------------------------------------------------

    def _open_create_dialog(self) -> None:
        dialog = UserCreateDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.email is None:
            return
        email, full_name = dialog.email, dialog.full_name or ""
        self._error_label.clear()

        def created(result: UserCreateResult) -> None:
            self._show_password(result.user.email, result.temporary_password)
            self.refresh()

        submit(lambda: self._api.admin_create_user(email, full_name), created, self._on_error)

    def _open_edit_dialog(self) -> None:
        user = self._selected
        if user is None:
            return
        dialog = UserEditDialog(user, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        changes = dialog.changes
        if not changes:
            return
        submit(
            lambda: self._api.admin_update_user(user.id, changes),
            lambda _user: self.refresh(),
            self._on_error,
        )

    def _reset_password(self) -> None:
        user = self._selected
        if user is None:
            return
        answer = QMessageBox.question(
            self, "Подтверждение",
            f"Сбросить пароль для {user.email}? Старый пароль перестанет действовать.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._error_label.clear()
        submit(
            lambda: self._api.admin_reset_password(user.id),
            lambda password, email=user.email: self._show_password(email, password),
            self._on_error,
        )

    def _toggle_active(self) -> None:
        user = self._selected
        if user is None:
            return
        if user.is_active:
            question = f"Деактивировать {user.email}? Пользователь потеряет вход в систему."
        else:
            question = f"Активировать {user.email} снова?"
        answer = QMessageBox.question(
            self, "Подтверждение", question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._error_label.clear()
        if user.is_active:
            action = lambda: self._api.admin_deactivate_user(user.id)  # noqa: E731
        else:
            action = lambda: self._api.admin_update_user(user.id, {"is_active": True})  # noqa: E731
        submit(action, lambda _result: self.refresh(), self._on_error)

    # --- Role actions ------------------------------------------------------------------------

    def _grant_access(self) -> None:
        user = self._selected
        quarry_id = self._grant_quarry_combo.currentData()
        role_name = self._grant_role_combo.currentText()
        if user is None or not quarry_id:
            return
        self._error_label.clear()

        def granted(_result: object, user_id: str = user.id) -> None:
            # Роль могла быть выдана самому себе — освежаем карту доступов UI
            self._state.request_access_refresh()
            submit(
                lambda: self._api.admin_user_access(user_id),
                self._render_accesses,
                self._on_error,
            )

        submit(
            lambda: self._api.admin_grant_access(quarry_id, user.id, role_name),
            granted,
            self._on_error,
        )

    def _revoke_access(self) -> None:
        user = self._selected
        rows = {item.row() for item in self._access_table.selectedItems()}
        if user is None or len(rows) != 1:
            return
        row = rows.pop()
        if not (0 <= row < len(self._accesses)):
            return
        access = self._accesses[row]
        answer = QMessageBox.question(
            self, "Подтверждение",
            f"Отозвать роль {access.role_name} на карьере «{access.quarry_name}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._error_label.clear()

        def revoked(_result: object, user_id: str = user.id) -> None:
            self._state.request_access_refresh()
            submit(
                lambda: self._api.admin_user_access(user_id),
                self._render_accesses,
                self._on_error,
            )

        submit(
            lambda: self._api.admin_revoke_access(access.quarry_id, access.access_id),
            revoked,
            self._on_error,
        )
