"""Main window: side-menu navigation + a stacked page area.

Scaffold shell — each screen is a placeholder for now. Screens are filled in as they are
ported (dashboard, quarries, sections, passports, capture, reports, recommendations,
admin). Login runs through the toolbar action: the blocking PKCE browser round-trip is
executed on QThreadPool, never on the UI thread.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QToolBar,
    QWidget,
)

if TYPE_CHECKING:
    from zmetrics_desktop.context import AppContext
    from zmetrics_desktop.offline.sync_processor import SyncReport

SYNC_INTERVAL_MS = 30_000  # drain the offline queue every 30 s

# (nav label, screen title) in display order.
SCREENS: list[tuple[str, str]] = [
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


class _LoginWorker(QRunnable):
    """Runs the blocking PKCE login off the UI thread."""

    class Signals(QObject):
        succeeded = Signal()
        failed = Signal(str)

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._context = context
        self.signals = self.Signals()

    def run(self) -> None:
        try:
            self._context.auth.login()
        except Exception as exc:  # AuthError or network failure
            self.signals.failed.emit(str(exc))
        else:
            self.signals.succeeded.emit()


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

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._nav = QListWidget()
        self._nav.setFixedWidth(220)
        self._nav.setObjectName("nav")

        from zmetrics_desktop.ui.state import AppState

        self._state = AppState()
        self._access_retry_count = 0
        self._state.access_refresh_requested.connect(self._load_access)

        self._stack = QStackedWidget()
        for nav_label, title in SCREENS:
            self._nav.addItem(nav_label)
            self._stack.addWidget(self._build_screen(nav_label, title))

        self._nav.currentRowChanged.connect(self._stack.setCurrentIndex)
        self._nav.setCurrentRow(0)

        layout.addWidget(self._nav)
        layout.addWidget(self._stack, stretch=1)
        self.setCentralWidget(central)

        if self._context is not None:
            self._build_auth_toolbar()
            self._build_sync_status()
            self._load_access()

    def _build_screen(self, nav_label: str, title: str) -> QWidget:
        """Real screen when implemented (needs a context), placeholder otherwise."""
        if self._context is None:
            return _placeholder(title)
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

    def _refresh_auth_ui(self) -> None:
        assert self._context is not None
        authenticated = self._context.auth.access_token() is not None
        self._auth_status.setText(
            "  Авторизован  " if authenticated else "  Не авторизован  "
        )
        self._login_action.setVisible(not authenticated)
        self._logout_action.setVisible(authenticated)

    def _start_login(self) -> None:
        assert self._context is not None
        self._login_action.setEnabled(False)
        worker = _LoginWorker(self._context)
        worker.signals.succeeded.connect(self._on_login_done)
        worker.signals.failed.connect(self._on_login_failed)
        self._login_worker = worker  # keep alive until the queued signal is delivered
        QThreadPool.globalInstance().start(worker)

    def _on_login_done(self) -> None:
        self._login_action.setEnabled(True)
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
        QMessageBox.warning(self, "Ошибка входа", message)

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
            text = "⚠ Оффлайн"
            if report.remaining:
                text += f" · в очереди: {report.remaining}"
        elif report.remaining or report.failed:
            text = f"Онлайн · в очереди: {report.remaining}"
            if report.failed:
                text += f" · ошибок: {report.failed}"
        else:
            text = "Онлайн"
        self._sync_status.setText(text)
