"""Main window: side-menu navigation + a stacked page area.

Login — форма логин/пароль прямо в приложении (direct access grant против публичного
клиента ``zmetrics-desktop``); браузер не открывается. Блокирующий запрос токена
выполняется на QThreadPool, никогда на UI-потоке. Пароль не сохраняется — в keyring
живут только токены.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from zmetrics_desktop.context import AppContext
    from zmetrics_desktop.offline.sync_processor import SyncReport

from zmetrics_desktop.ui.errors import human_error

SYNC_INTERVAL_MS = 30_000  # drain the offline queue every 30 s
AUTH_CHECK_INTERVAL_MS = 60_000  # проверка срока access-токена раз в минуту
AUTH_REFRESH_MARGIN_S = 180.0  # обновляем за 3 минуты до истечения, не ждём 401

# (nav label, screen title) in display order.
SCREENS: list[tuple[str, str]] = [
    ("Подключение", "Подключение к серверу"),
    ("Дашборд", "Дашборд"),
    ("Карьеры", "Карьеры"),
    ("Участки", "Участки / блоки"),
    ("Паспорта БВР", "Паспорта БВР"),
    ("Съёмка", "Съёмка и анализ (ZED 2)"),
    ("Отчёты", "Отчёты"),
    ("Рекомендации", "Рекомендации"),
    ("Администрирование", "Администрирование"),
]


def _placeholder(title: str) -> QWidget:
    page = QWidget()
    layout = QHBoxLayout(page)
    label = QLabel(f"{title}\n\n(экран в разработке)")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)
    return page


class _LoginDialog(QDialog):
    """Форма логина в приложении — без браузера."""

    def __init__(self, parent: QWidget | None = None, username: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("Вход в ZMetrics")
        self.setModal(True)
        form = QFormLayout(self)
        self._username = QLineEdit(username)
        self._username.setPlaceholderText("логин")
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText("пароль")
        form.addRow("Логин:", self._username)
        form.addRow("Пароль:", self._password)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Войти")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        (self._password if username else self._username).setFocus()

    def credentials(self) -> tuple[str, str]:
        return self._username.text().strip(), self._password.text()


class _LoginWorker(QRunnable):
    """Runs the blocking password-grant login off the UI thread."""

    class Signals(QObject):
        succeeded = Signal()
        failed = Signal(str)

    def __init__(self, context: AppContext, username: str, password: str) -> None:
        super().__init__()
        self._context = context
        self._username = username
        self._password = password
        self.signals = self.Signals()

    def run(self) -> None:
        try:
            self._context.auth.login_password(self._username, self._password)
        except Exception as exc:  # AuthError or network failure
            self.signals.failed.emit(str(exc))
        else:
            self.signals.succeeded.emit()
        finally:
            self._password = ""  # не держим пароль в памяти дольше необходимого


class _RefreshWorker(QRunnable):
    """Runs the blocking token refresh off the UI thread."""

    class Signals(QObject):
        finished = Signal(str)  # "ok" | "expired" | "offline"

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._context = context
        self.signals = self.Signals()

    def run(self) -> None:
        try:
            outcome = self._context.auth.refresh_outcome()
        except Exception:  # не роняем UI из-за неожиданной ошибки — попробуем позже
            outcome = "offline"
        self.signals.finished.emit(outcome)


class _SyncWorker(QRunnable):
    """One offline-queue drain pass off the UI thread (own sqlite connection)."""

    class Signals(QObject):
        finished = Signal(object)  # SyncReport

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._context = context
        self.signals = self.Signals()

    def run(self) -> None:
        queue = self._context.make_sync_manager()
        try:
            report = self._context.make_sync_processor(queue).process_once()
        finally:
            queue.close()
        self.signals.finished.emit(report)


class MainWindow(QMainWindow):
    def __init__(self, context: AppContext | None = None) -> None:
        super().__init__()
        self._context = context
        self.setWindowTitle("ZMetrics")
        self.resize(1200, 800)
        self._apply_light_theme()

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = self._build_sidebar()

        from zmetrics_desktop.ui.state import AppState

        self._state = AppState()
        self._access_retry_count = 0
        self._last_username = ""
        self._state.access_refresh_requested.connect(self._load_access)

        self._stack = QStackedWidget()
        for nav_label, title in SCREENS:
            self._nav.addItem(nav_label)
            self._stack.addWidget(self._build_screen(nav_label, title))

        self._nav.currentRowChanged.connect(self._stack.setCurrentIndex)
        self._nav.setCurrentRow(0)

        layout.addWidget(sidebar)
        layout.addWidget(self._stack, stretch=1)
        self.setCentralWidget(central)

        if self._context is not None:
            self._build_auth_toolbar()
            self._build_sync_status()
            self._load_access()

    def _apply_light_theme(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f5f7fa;
            }
            QWidget {
                color: #203040;
            }
            QLabel {
                color: #203040;
            }
            QToolBar, QStatusBar {
                background: #edf2f7;
                border: 0;
                color: #394b5f;
                spacing: 8px;
            }
            QToolBar {
                border-bottom: 1px solid #d7dee8;
                padding: 6px 10px;
            }
            QToolBar QLabel, QStatusBar QLabel {
                color: #394b5f;
            }
            QToolBar QToolButton {
                background: #ffffff;
                border: 1px solid #b8c7d8;
                border-radius: 5px;
                color: #243447;
                min-height: 26px;
                padding: 4px 12px;
                margin-left: 6px;
            }
            QToolBar QToolButton:hover {
                background: #f1f6fb;
                border-color: #7fa7d5;
            }
            QToolBar QToolButton:pressed {
                background: #d9ebff;
            }
            QToolBar QToolButton:disabled {
                background: #eef1f5;
                color: #8b98a8;
            }
            QGroupBox {
                border: 1px solid #d7dee8;
                border-radius: 6px;
                margin-top: 12px;
                padding: 12px 10px 10px 10px;
                background: #ffffff;
                color: #263545;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QPushButton {
                background: #ffffff;
                border: 1px solid #c8d2df;
                border-radius: 5px;
                color: #243447;
                min-height: 26px;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background: #f1f6fb;
                border-color: #9bb4cf;
            }
            QPushButton:pressed {
                background: #e5eef8;
            }
            QPushButton:disabled {
                background: #eef1f5;
                color: #8b98a8;
            }
            QLineEdit, QComboBox, QTextEdit, QPlainTextEdit {
                background: #ffffff;
                border: 1px solid #c8d2df;
                border-radius: 5px;
                color: #203040;
                min-height: 28px;
                padding: 3px 8px;
            }
            QTextEdit, QPlainTextEdit {
                selection-background-color: #d9ebff;
                selection-color: #152638;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {
                border-color: #2f80ed;
            }
            QTableWidget, QTableView {
                background: #ffffff;
                alternate-background-color: #f6f8fb;
                border: 1px solid #d7dee8;
                gridline-color: #e1e7ef;
                selection-background-color: #d9ebff;
                selection-color: #152638;
            }
            QHeaderView::section {
                background: #edf2f7;
                border: 0;
                border-right: 1px solid #d7dee8;
                border-bottom: 1px solid #d7dee8;
                color: #394b5f;
                padding: 6px 8px;
                font-weight: 600;
            }
            QListWidget {
                background: #ffffff;
                border: 1px solid #d7dee8;
                border-radius: 5px;
                color: #203040;
                selection-background-color: #d9ebff;
                selection-color: #152638;
            }
            QListWidget::item {
                padding: 6px 8px;
            }
            """
        )

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(
            """
            QWidget#sidebar {
                background: #202936;
                color: #e8eef5;
            }
            QLabel#brandTitle {
                color: #ffffff;
                font-size: 21px;
                font-weight: 700;
            }
            QLabel#brandSubtitle {
                color: #aebdca;
                font-size: 12px;
            }
            QListWidget#nav {
                background: transparent;
                border: 0;
                color: #dce7f2;
                outline: 0;
                padding: 4px 0;
            }
            QListWidget#nav::item {
                padding: 10px 14px;
                margin: 2px 10px;
                border-radius: 6px;
            }
            QListWidget#nav::item:selected {
                background: #2f80ed;
                color: #ffffff;
            }
            QListWidget#nav::item:hover:!selected {
                background: #303d4d;
            }
            """
        )
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 18, 0, 12)
        layout.setSpacing(12)

        title = QLabel("ZMetrics")
        title.setObjectName("brandTitle")
        title.setContentsMargins(18, 0, 18, 0)
        layout.addWidget(title)

        subtitle = QLabel("Полевой клиент")
        subtitle.setObjectName("brandSubtitle")
        subtitle.setContentsMargins(18, 0, 18, 4)
        layout.addWidget(subtitle)

        self._nav = QListWidget()
        self._nav.setObjectName("nav")
        layout.addWidget(self._nav, stretch=1)
        return sidebar

    def _build_screen(self, nav_label: str, title: str) -> QWidget:
        """Real screen when implemented (needs a context), placeholder otherwise."""
        if self._context is None:
            return _placeholder(title)
        if nav_label == "Подключение":
            from zmetrics_desktop.ui.connection import ConnectionScreen

            return ConnectionScreen(self._context, self._state)
        if nav_label == "Дашборд":
            from zmetrics_desktop.ui.dashboard import DashboardScreen

            return DashboardScreen(self._context, self._state)
        if nav_label == "Карьеры":
            from zmetrics_desktop.ui.quarries import QuarriesScreen

            return QuarriesScreen(self._context, self._state)
        if nav_label == "Участки":
            from zmetrics_desktop.ui.sections import SectionsScreen

            return SectionsScreen(self._context, self._state)
        if nav_label == "Паспорта БВР":
            from zmetrics_desktop.ui.passports import PassportsScreen

            return PassportsScreen(self._context, self._state)
        if nav_label == "Съёмка":
            from zmetrics_desktop.ui.capture import CaptureScreen

            return CaptureScreen(self._context, self._state)
        if nav_label == "Отчёты":
            from zmetrics_desktop.ui.reports import ReportsScreen

            return ReportsScreen(self._context, self._state)
        if nav_label == "Рекомендации":
            from zmetrics_desktop.ui.recommendations import RecommendationsScreen

            return RecommendationsScreen(self._context, self._state)
        if nav_label == "Администрирование":
            from zmetrics_desktop.ui.admin import AdminScreen

            return AdminScreen(self._context, self._state)
        return _placeholder(title)

    # --- Auth toolbar -----------------------------------------------------------

    def _build_auth_toolbar(self) -> None:
        toolbar = QToolBar("auth")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._auth_status = QLabel()
        toolbar.addWidget(self._auth_status)

        self._login_action = toolbar.addAction("Войти", self._start_login)
        self._logout_action = toolbar.addAction("Выйти", self._logout)
        self._refresh_auth_ui()

        # AUTH-2: проактивное обновление токена по таймеру — не ждём 401 на экранах
        self._refresh_running = False
        self._session_expired_shown = False
        self._auth_timer = QTimer(self)
        self._auth_timer.setInterval(AUTH_CHECK_INTERVAL_MS)
        self._auth_timer.timeout.connect(self._auth_tick)
        self._auth_timer.start()
        QTimer.singleShot(0, self._auth_tick)  # первый чек сразу после старта

    def _refresh_auth_ui(self) -> None:
        assert self._context is not None
        authenticated = self._context.auth.access_token() is not None
        if authenticated:
            text = "  Авторизован  "
            session_exp = self._context.auth.session_expires_at()
            if session_exp:
                from datetime import datetime

                until = datetime.fromtimestamp(session_exp).strftime("%H:%M")
                text = f"  Авторизован до {until}  "
            self._auth_status.setText(text)
        else:
            self._auth_status.setText("  Не авторизован  ")
        self._login_action.setVisible(not authenticated)
        self._logout_action.setVisible(authenticated)

    # --- Proactive token refresh (AUTH-2) -------------------------------------------

    def _auth_tick(self) -> None:
        assert self._context is not None
        if self._refresh_running or self._context.auth.access_token() is None:
            return
        import time

        expires_at = self._context.auth.access_expires_at()
        # Неизвестный срок (старый keyring без expires_at) тоже обновляем — получим срок.
        if expires_at is not None and expires_at - time.time() > AUTH_REFRESH_MARGIN_S:
            return
        self._refresh_running = True
        worker = _RefreshWorker(self._context)
        worker.signals.finished.connect(self._on_refresh_outcome)
        self._refresh_worker = worker  # keep alive until the queued signal is delivered
        QThreadPool.globalInstance().start(worker)

    def _on_refresh_outcome(self, outcome: str) -> None:
        self._refresh_running = False
        if outcome == "ok":
            self._session_expired_shown = False
            self._refresh_auth_ui()
            return
        if outcome == "offline":
            return  # сеть вернётся — обновим на следующем тике
        # expired: смена закончилась — явный диалог вместо тихих 401 по всем экранам
        assert self._context is not None
        self._context.auth.logout()
        self._refresh_auth_ui()
        if self._session_expired_shown:
            return
        self._session_expired_shown = True
        QMessageBox.information(
            self,
            "Сессия истекла",
            "Рабочая сессия закончилась. Войдите снова, чтобы продолжить.",
        )
        self._start_login()

    def _start_login(self) -> None:
        assert self._context is not None
        dialog = _LoginDialog(self, username=self._last_username)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        username, password = dialog.credentials()
        if not username or not password:
            return
        self._last_username = username  # удобство повторного входа; пароль не храним
        self._login_action.setEnabled(False)
        worker = _LoginWorker(self._context, username, password)
        worker.signals.succeeded.connect(self._on_login_done)
        worker.signals.failed.connect(self._on_login_failed)
        self._login_worker = worker  # keep alive until the queued signal is delivered
        QThreadPool.globalInstance().start(worker)

    def _on_login_done(self) -> None:
        self._login_action.setEnabled(True)
        self._session_expired_shown = False
        self._refresh_auth_ui()
        self._load_access()

    def _load_access(self) -> None:
        """Fetch the caller's per-quarry roles for UI button gating (fail closed:
        until this succeeds, write buttons stay hidden).

        Раньше ошибка глоталась молча и карта оставалась пустой до перезапуска —
        админ выглядел бесправным. Теперь ретраим с паузой, пока не получится.
        """
        assert self._context is not None
        if self._context.auth.access_token() is None:
            return
        from PySide6.QtCore import QTimer

        from zmetrics_desktop.api.zmetrics import ZMetricsApi
        from zmetrics_desktop.ui.workers import submit

        api = ZMetricsApi(self._context.api)

        def loaded(entries: object) -> None:
            self._access_retry_count = 0
            self._state.set_access(entries)  # type: ignore[arg-type]

        def failed(_message: str) -> None:
            if self._access_retry_count >= 5:
                return  # дальше — по явному действию (логин/обновление экрана)
            self._access_retry_count += 1
            QTimer.singleShot(5_000, self._load_access)

        submit(api.get_my_access, loaded, failed)

    def _on_login_failed(self, message: str) -> None:
        self._login_action.setEnabled(True)
        self._refresh_auth_ui()
        QMessageBox.warning(self, "Ошибка входа", human_error(message))

    def _logout(self) -> None:
        assert self._context is not None
        self._context.auth.logout()
        self._refresh_auth_ui()

    # --- Offline queue sync -------------------------------------------------------

    def _build_sync_status(self) -> None:
        self._sync_status = QLabel("Соединение…")
        self.statusBar().addPermanentWidget(self._sync_status)
        self._sync_running = False

        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(SYNC_INTERVAL_MS)
        self._sync_timer.timeout.connect(self._start_sync)
        self._sync_timer.start()
        QTimer.singleShot(0, self._start_sync)  # first pass right after startup

    def _start_sync(self) -> None:
        assert self._context is not None
        if self._sync_running:  # never overlap two drain passes
            return
        self._sync_running = True
        worker = _SyncWorker(self._context)
        worker.signals.finished.connect(self._on_sync_finished)
        self._sync_worker = worker  # keep alive until the queued signal is delivered
        QThreadPool.globalInstance().start(worker)

    def _on_sync_finished(self, report: SyncReport) -> None:
        self._sync_running = False
        if not report.online:
            text = "Сервер недоступен"
            if report.remaining:
                text += f" · в очереди: {report.remaining}"
        elif report.remaining or report.failed:
            text = f"Онлайн · в очереди: {report.remaining}"
            if report.failed:
                text += f" · ошибок: {report.failed}"
        else:
            text = "Онлайн"
        self._sync_status.setText(text)
