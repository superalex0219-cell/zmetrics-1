"""Server connection settings screen."""
from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from zmetrics_desktop.config import save_user_server_settings, user_env_path
from zmetrics_desktop.ui.errors import human_error
from zmetrics_desktop.ui.layout import (
    apply_form_layout,
    apply_screen_layout,
    configure_wrapping_label,
)
from zmetrics_desktop.ui.workers import submit

if TYPE_CHECKING:
    from zmetrics_desktop.context import AppContext
    from zmetrics_desktop.ui.state import AppState


class ConnectionScreen(QWidget):
    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._context = context
        self._state = state

        root = QVBoxLayout(self)
        apply_screen_layout(root)

        title = QLabel("Подключение к серверу")
        title.setObjectName("pageTitle")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        root.addWidget(title)

        intro = QLabel(
            "Адреса сохраняются в пользовательские настройки приложения. "
            "После сохранения перезапустите ZMetrics, чтобы все экраны и вход использовали новый сервер."
        )
        configure_wrapping_label(intro)
        intro.setStyleSheet("color: #52616f;")
        root.addWidget(intro)

        box = QGroupBox("Сервер")
        form = QFormLayout(box)
        apply_form_layout(form)
        self._backend_url = QLineEdit(context.settings.backend_base_url)
        self._backend_url.setPlaceholderText("http://192.168.0.10:8000")
        self._keycloak_url = QLineEdit(context.settings.keycloak_base_url)
        self._keycloak_url.setPlaceholderText("http://192.168.0.10:8080")
        self._realm = QLineEdit(context.settings.keycloak_realm)
        self._client_id = QLineEdit(context.settings.keycloak_client_id)
        self._timeout = QLineEdit(str(context.settings.request_timeout_s))
        form.addRow("Backend API:", self._backend_url)
        form.addRow("Keycloak:", self._keycloak_url)
        form.addRow("Realm:", self._realm)
        form.addRow("Client ID:", self._client_id)
        form.addRow("Таймаут, сек:", self._timeout)
        root.addWidget(box)

        actions = QHBoxLayout()
        self._save_button = QPushButton("Сохранить")
        self._save_button.clicked.connect(self._save)
        actions.addWidget(self._save_button)
        self._test_button = QPushButton("Проверить сервер")
        self._test_button.clicked.connect(self._test_backend)
        actions.addWidget(self._test_button)
        actions.addStretch(1)
        root.addLayout(actions)

        self._status = QLabel()
        configure_wrapping_label(self._status)
        self._status.setTextFormat(Qt.TextFormat.PlainText)
        self._status.setStyleSheet(
            "padding: 10px 12px; border-radius: 6px; background: #eef4ff; color: #21456b;"
        )
        self._status.setText(f"Текущий файл настроек: {user_env_path()}")
        root.addWidget(self._status)
        root.addStretch(1)

    def _values(self) -> dict[str, str | float]:
        timeout_text = self._timeout.text().strip().replace(",", ".")
        timeout = float(timeout_text) if timeout_text else self._context.settings.request_timeout_s
        return {
            "backend_base_url": self._backend_url.text().strip().rstrip("/"),
            "keycloak_base_url": self._keycloak_url.text().strip().rstrip("/"),
            "keycloak_realm": self._realm.text().strip(),
            "keycloak_client_id": self._client_id.text().strip(),
            "request_timeout_s": timeout,
        }

    def _save(self) -> None:
        try:
            path = save_user_server_settings(self._values())
        except Exception as exc:
            self._set_error(str(exc))
            return
        self._set_ok(f"Сохранено: {path}\nПерезапустите ZMetrics, чтобы применить настройки.")

    def _test_backend(self) -> None:
        values = self._values()
        base_url = str(values["backend_base_url"]).rstrip("/")
        timeout = float(values["request_timeout_s"])
        self._test_button.setEnabled(False)
        self._set_neutral("Проверяю /health на backend...")

        def check() -> str:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(f"{base_url}/health")
                response.raise_for_status()
            return base_url

        def done(url: object) -> None:
            self._test_button.setEnabled(True)
            self._set_ok(f"Backend доступен: {url}")

        def failed(message: str) -> None:
            self._test_button.setEnabled(True)
            self._set_error(human_error(message))

        submit(check, done, failed)

    def _set_neutral(self, text: str) -> None:
        self._status.setStyleSheet(
            "padding: 10px 12px; border-radius: 6px; background: #eef4ff; color: #21456b;"
        )
        self._status.setText(text)

    def _set_ok(self, text: str) -> None:
        self._status.setStyleSheet(
            "padding: 10px 12px; border-radius: 6px; background: #e8f7ed; color: #1f6b3a;"
        )
        self._status.setText(text)

    def _set_error(self, text: str) -> None:
        self._status.setStyleSheet(
            "padding: 10px 12px; border-radius: 6px; background: #fff1f0; color: #9f2a1d;"
        )
        self._status.setText(text)
