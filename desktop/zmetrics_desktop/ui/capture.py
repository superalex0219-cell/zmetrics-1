"""Capture & analysis screen: live UVC preview, frame upload, job polling, P80.

Поток: превью стартует само (ZED выбирается приоритетно) → чек-лист готовности
подсказывает, чего не хватает → «Снять и отправить» (нужна роль surveyor) →
онлайн: capture session + кадры + analysis job, поллинг статуса каждые 2 с → P10/P50/P80;
оффлайн: кадры сохраняются на диск, составная операция уходит в очередь SyncManager и
доливается автоматически (статус-бар).

«Зарегистрировать ZED» качает заводскую калибровку с calib.stereolabs.com по
серийнику и создаёт Device + Calibration — без консольных скриптов.

Веб-камера без ZED определяется как моно (aspect < 1.8) — грузится только left_frame,
серверный пайплайн сам падает в mock-ветку стерео. CV остаётся на сервере.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import TYPE_CHECKING

import numpy as np

from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QHideEvent, QIcon, QImage, QPixmap, QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from zmetrics_desktop.api.client import ApiError
from zmetrics_desktop.api.zmetrics import ZMetricsApi
from zmetrics_desktop.capture.camera import CameraError, CameraInfo, StereoCamera, list_cameras
from zmetrics_desktop.capture.stereo import StereoFrame, encode_jpeg
from zmetrics_desktop.capture.zed_calibration import (
    ZedConfError,
    build_calibration_payload,
    fetch_conf_text,
    parse_zed_conf,
    resolution_for_frame,
)
from zmetrics_desktop.models import (
    AnalysisJob,
    AnalysisResult,
    BlastPassport,
    Calibration,
    CaptureSessionSummary,
    Device,
    Quarry,
)
from zmetrics_desktop.offline.capture_upload import (
    KIND_CAPTURE_UPLOAD,
    build_series_payload,
    perform_capture_upload,
)
from zmetrics_desktop.ui.errors import human_error
from zmetrics_desktop.ui.passports import STATUS_RU, _fmt
from zmetrics_desktop.ui.state import ROLE_SURVEYOR
from zmetrics_desktop.ui.workers import submit

if TYPE_CHECKING:
    from zmetrics_desktop.context import AppContext
    from zmetrics_desktop.ui.state import AppState

JOB_POLL_INTERVAL_MS = 2_000
JOB_POLL_LIMIT = 300  # ~10 минут — дальше пользователь смотрит «Отчёты»

JOB_STATUS_RU = {
    "queued": "в очереди",
    "running": "выполняется",
    "completed": "завершён",
    "failed": "ошибка",
}

# Калибровка-заглушка для тестовой веб-камеры: мок-пайплайну матрицы не нужны,
# реальное стерео с такой калибровкой считать нельзя (устройство помечается в notes).
_STUB_MATRIX = {"rows": 3, "cols": 3, "data": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]}
_STUB_DIST = {"rows": 1, "cols": 5, "data": [0.0, 0.0, 0.0, 0.0, 0.0]}


class _PreviewWorker(QRunnable):
    """Reads frames off the UI thread and emits them until stopped."""

    class Signals(QObject):
        frame = Signal(object)  # StereoFrame
        error = Signal(str)
        stopped = Signal()

    def __init__(self, camera_index: int, interval_s: float = 0.15) -> None:
        super().__init__()
        self._index = camera_index
        self._interval_s = interval_s
        self._stop = threading.Event()
        self.signals = self.Signals()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        try:
            with StereoCamera(self._index) as camera:
                while not self._stop.is_set():
                    self.signals.frame.emit(camera.read())
                    time.sleep(self._interval_s)
        except (CameraError, Exception) as exc:  # cv2 may raise anything
            if not self._stop.is_set():
                self.signals.error.emit(str(exc))
        finally:
            self.signals.stopped.emit()


class CaptureScreen(QWidget):
    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._context = context
        self._api = ZMetricsApi(context.api)
        self._state = state
        self._loaded_once = False
        self._passports: list[BlastPassport] = []
        self._devices: list[Device] = []
        self._calibrations: list[Calibration] = []
        self._cameras: list[CameraInfo] = []
        self._last_frame: StereoFrame | None = None
        self._last_preview_pixmap: QPixmap | None = None
        self._preview_worker: _PreviewWorker | None = None
        # CAP-MULTI: серия пар кадров; каждый элемент {left_jpg, right_jpg|None, stereo}
        self._series: list[dict] = []
        self._job_ref: tuple[str, list[str]] | None = None  # (session_id, [job_id, ...])
        self._poll_count = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("Съёмка ZED 2")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        root.addWidget(title)

        self._status_banner = QLabel("Выберите карьер, камеру и паспорт для съёмки.")
        self._status_banner.setWordWrap(True)
        root.addWidget(self._status_banner)
        self._set_status("neutral", "Выберите карьер, камеру и паспорт для съёмки.")

        # --- Context selectors -----------------------------------------------------
        selectors_box = QGroupBox("Контекст съёмки")
        selectors = QFormLayout()
        selectors_box.setLayout(selectors)
        self._passport_combo = QComboBox()
        selectors.addRow("Паспорт (утв./активный):", self._passport_combo)
        device_block = QVBoxLayout()
        device_row = QHBoxLayout()
        self._device_combo = QComboBox()
        self._device_combo.currentIndexChanged.connect(self._on_device_selected)
        device_row.addWidget(self._device_combo, stretch=1)
        self._calibration_combo = QComboBox()
        device_row.addWidget(self._calibration_combo, stretch=1)
        device_block.addLayout(device_row)
        device_actions = QHBoxLayout()
        self._register_zed_button = QPushButton("Зарегистрировать ZED")
        self._register_zed_button.setToolTip(
            "Скачивает заводскую калибровку с calib.stereolabs.com по серийному\n"
            "номеру (на наклейке камеры) и регистрирует устройство + калибровку."
        )
        self._register_zed_button.clicked.connect(self._register_zed)
        device_actions.addWidget(self._register_zed_button)
        self._prepare_button = QPushButton("Подготовить тестовое устройство")
        self._prepare_button.setToolTip(
            "Регистрирует выбранную камеру как Device и создаёт калибровку-заглушку.\n"
            "Только для тестов без ZED 2 — реальное стерео с ней не считается."
        )
        self._prepare_button.clicked.connect(self._prepare_test_device)
        device_actions.addWidget(self._prepare_button)
        device_actions.addStretch(1)
        device_block.addLayout(device_actions)
        selectors.addRow("Устройство / калибровка:", device_block)
        root.addWidget(selectors_box)

        # --- Camera + preview --------------------------------------------------------
        camera_box = QGroupBox("Камера и превью")
        camera_layout = QVBoxLayout(camera_box)
        camera_row = QHBoxLayout()
        camera_row.addWidget(QLabel("Камера:"))
        self._camera_combo = QComboBox()
        camera_row.addWidget(self._camera_combo, stretch=1)
        self._preview_button = QPushButton("Старт превью")
        self._preview_button.clicked.connect(self._toggle_preview)
        camera_row.addWidget(self._preview_button)
        self._mode_label = QLabel("")
        camera_row.addWidget(self._mode_label)
        camera_row.addStretch(1)
        camera_layout.addLayout(camera_row)

        body = QHBoxLayout()
        self._preview_label = QLabel("Превью выключено")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setMinimumSize(320, 200)
        self._preview_label.setStyleSheet(
            "background: #18202a; color: #9aa8b5; border: 1px solid #2e3a48; border-radius: 6px;"
        )
        body.addWidget(self._preview_label, stretch=3)
        body.addWidget(self._build_result_panel(), stretch=2)
        camera_layout.addLayout(body, stretch=1)
        root.addWidget(camera_box, stretch=1)

        # --- Серия снимков (CAP-MULTI): несколько пар кадров в одну сессию -----------
        series_box = QGroupBox("Серия снимков")
        series_layout = QVBoxLayout(series_box)
        series_buttons = QGridLayout()
        self._add_shot_button = QPushButton("Снять ещё (в серию)")
        self._add_shot_button.setToolTip(
            "Добавляет текущий кадр превью в серию — все кадры серии уйдут\n"
            "одной сессией, на каждую пару будет свой анализ."
        )
        self._add_shot_button.clicked.connect(self._add_current_to_series)
        series_buttons.addWidget(self._add_shot_button, 0, 0)
        self._load_disk_button = QPushButton("Загрузить с диска…")
        self._load_disk_button.setToolTip(
            "JPEG/PNG с диска; широкие кадры (SBS) автоматически делятся на left/right."
        )
        self._load_disk_button.clicked.connect(self._load_from_disk)
        series_buttons.addWidget(self._load_disk_button, 0, 1)
        self._remove_shot_button = QPushButton("Удалить выбранный")
        self._remove_shot_button.clicked.connect(self._remove_selected_shot)
        series_buttons.addWidget(self._remove_shot_button, 1, 0)
        self._clear_series_button = QPushButton("Очистить серию")
        self._clear_series_button.clicked.connect(self._clear_series)
        series_buttons.addWidget(self._clear_series_button, 1, 1)
        series_buttons.setColumnStretch(0, 1)
        series_buttons.setColumnStretch(1, 1)
        series_layout.addLayout(series_buttons)
        self._series_list = QListWidget()
        self._series_list.setViewMode(QListWidget.ViewMode.IconMode)
        self._series_list.setIconSize(QSize(96, 60))
        self._series_list.setFixedHeight(96)
        self._series_list.setFlow(QListWidget.Flow.LeftToRight)
        self._series_list.setWrapping(False)
        series_layout.addWidget(self._series_list)
        root.addWidget(series_box)

        # Чек-лист готовности: что ещё нужно сделать, чтобы кнопка съёмки ожила
        self._ready_label = QLabel("")
        self._ready_label.setWordWrap(True)
        root.addWidget(self._ready_label)

        actions = QHBoxLayout()
        self._capture_button = QPushButton("Снять и отправить на анализ")
        self._capture_button.setEnabled(False)
        self._capture_button.clicked.connect(self._capture_and_send)
        actions.addWidget(self._capture_button)
        actions.addStretch(1)
        self._error_label = QLabel()
        self._error_label.setStyleSheet(
            "padding: 8px 10px; border-radius: 6px; background: #fff1f0; color: #9f2a1d;"
        )
        self._error_label.setWordWrap(True)
        actions.addWidget(self._error_label, stretch=1)
        root.addLayout(actions)

        # --- Снимки взрыва: сессии выбранного паспорта с агрегатами ------------------
        summary_box = QGroupBox("Снимки взрыва")
        summary_layout = QVBoxLayout(summary_box)
        summary_header = QHBoxLayout()
        self._summary_refresh_button = QPushButton("Обновить")
        self._summary_refresh_button.clicked.connect(self._load_summary)
        summary_header.addWidget(self._summary_refresh_button)
        summary_header.addStretch(1)
        summary_layout.addLayout(summary_header)
        self._summary_label = QLabel("—")
        self._summary_label.setWordWrap(True)
        self._summary_label.setTextFormat(Qt.TextFormat.RichText)
        summary_layout.addWidget(self._summary_label)
        root.addWidget(summary_box)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(JOB_POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll_job)

        self._state.quarry_changed.connect(self._on_state_quarry_changed)
        self._state.access_changed.connect(self._apply_role_gating)
        self._passport_combo.currentIndexChanged.connect(lambda *_: self._apply_role_gating())
        self._passport_combo.currentIndexChanged.connect(lambda *_: self._load_summary())
        self._calibration_combo.currentIndexChanged.connect(lambda *_: self._apply_role_gating())
        self._select_device_serial: str | None = None  # выбрать после _load_devices()

    def _build_result_panel(self) -> QWidget:
        box = QGroupBox("Анализ")
        form = QFormLayout(box)
        self._result_labels: dict[str, QLabel] = {}
        for key, label in [
            ("job", "Задача:"),
            ("p10", "P10:"),
            ("p50", "P50:"),
            ("p80", "P80:"),
            ("confidence", "Confidence:"),
            ("notes", "Примечания:"),
        ]:
            value = QLabel("—")
            value.setWordWrap(True)
            self._result_labels[key] = value
            form.addRow(label, value)
        return box

    def _set_status(self, kind: str, text: str) -> None:
        colors = {
            "ok": ("#e8f7ed", "#1f6b3a"),
            "warning": ("#fff6df", "#7b5100"),
            "error": ("#fff1f0", "#9f2a1d"),
            "neutral": ("#eef4ff", "#21456b"),
        }
        bg, fg = colors.get(kind, colors["neutral"])
        self._status_banner.setStyleSheet(
            f"padding: 10px 12px; border-radius: 6px; background: {bg}; color: {fg};"
        )
        self._status_banner.setText(text)

    def _show_error(self, message: str) -> None:
        text = human_error(message)
        self._error_label.setText(text)
        if text:
            self._set_status("error", text)

    def _clear_error(self) -> None:
        self._error_label.clear()

    # --- Loading ----------------------------------------------------------------------

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 — Qt naming
        super().showEvent(event)
        if not self._loaded_once:
            self._loaded_once = True
            self.refresh()
        else:
            # hideEvent освобождает камеру — при возврате на экран включаем снова
            self._maybe_autostart_preview()

    def hideEvent(self, event: QHideEvent) -> None:  # noqa: N802 — Qt naming
        super().hideEvent(event)
        self._stop_preview()  # release the camera when leaving the screen

    def resizeEvent(self, event: object) -> None:  # noqa: N802 — Qt naming
        super().resizeEvent(event)  # type: ignore[arg-type]
        self._render_preview_pixmap()

    def refresh(self) -> None:
        self._clear_error()
        self._load_cameras()
        self._load_devices()
        quarry = self._state.quarry
        if quarry is not None:
            self._load_passports(quarry)
        self._apply_role_gating()

    def _load_cameras(self) -> None:
        def list_safe() -> list[CameraInfo]:
            try:
                return list_cameras()
            except Exception:  # pygrabber missing / no devices
                return []

        submit(list_safe, self._on_cameras, self._show_error)

    def _on_cameras(self, cameras: list[CameraInfo]) -> None:
        self._cameras = cameras
        self._camera_combo.clear()
        for camera in cameras:
            label = camera.name + (" (ZED)" if camera.looks_like_zed else "")
            self._camera_combo.addItem(label, camera.index)
        if not cameras:
            self._camera_combo.addItem("Камеры не найдены", -1)
            self._set_status(
                "warning",
                "Камера не выбрана. Подключите ZED 2 и проверьте доступ к камере в macOS.",
            )
            return
        # ZED — приоритетный выбор; превью включаем сразу, без лишнего клика
        zed_idx = next((i for i, c in enumerate(cameras) if c.looks_like_zed), None)
        if zed_idx is not None:
            self._camera_combo.setCurrentIndex(zed_idx)
            self._set_status("neutral", "ZED 2 выбрана, запускаю превью.")
        else:
            self._set_status("neutral", "Камера найдена. Для ZED 2 выберите её в списке.")
        self._maybe_autostart_preview()

    def _load_passports(self, quarry: Quarry) -> None:
        submit(
            lambda: self._api.list_passports(quarry.id),
            self._on_passports,
            self._show_error,
        )

    def _on_passports(self, passports: list[BlastPassport]) -> None:
        # Capture session требует зафиксированный взрыв — он бывает только у
        # утверждённых/активных/завершённых паспортов.
        self._passports = [p for p in passports if p.status in ("approved", "active", "completed")]
        self._passport_combo.clear()
        for passport in self._passports:
            status = STATUS_RU.get(passport.status, passport.status)
            self._passport_combo.addItem(
                f"Ревизия {passport.revision_number} · {status} · {passport.id[:8]}",
                passport.id,
            )
        if not self._passports:
            self._passport_combo.addItem("Нет паспортов со взрывом", None)
        self._apply_role_gating()

    def _load_devices(self) -> None:
        submit(self._api.list_devices, self._on_devices, self._show_error)

    def _on_devices(self, devices: list[Device]) -> None:
        self._devices = devices
        self._device_combo.blockSignals(True)
        self._device_combo.clear()
        for device in devices:
            self._device_combo.addItem(f"{device.model} ({device.serial_number})", device.id)
        self._device_combo.blockSignals(False)
        if devices:
            target = self._select_device_serial
            self._select_device_serial = None
            index = next(
                (i for i, d in enumerate(devices) if d.serial_number == target), 0
            )
            self._device_combo.setCurrentIndex(index)
            self._on_device_selected(index)
        else:
            self._calibration_combo.clear()
            self._apply_role_gating()

    def _on_device_selected(self, index: int) -> None:
        if not (0 <= index < len(self._devices)):
            return
        device = self._devices[index]
        submit(
            lambda: self._api.list_calibrations(device.id),
            self._on_calibrations,
            self._show_error,
        )

    def _on_calibrations(self, calibrations: list[Calibration]) -> None:
        self._calibrations = calibrations
        self._calibration_combo.clear()
        for calibration in calibrations:
            active = " · активная" if calibration.is_active else ""
            self._calibration_combo.addItem(
                f"{calibration.image_width_px}×{calibration.image_height_px},"
                f" base {calibration.baseline_mm:g} мм{active}",
                calibration.id,
            )
        if not calibrations:
            self._calibration_combo.addItem("Нет калибровок", None)
        self._apply_role_gating()

    def _on_state_quarry_changed(self, quarry: object) -> None:
        if self._loaded_once and quarry is not None:
            self._load_passports(quarry)  # type: ignore[arg-type]

    def _apply_role_gating(self, *_: object) -> None:
        quarry = self._state.quarry
        allowed = self._state.role_level(quarry.id if quarry else None) >= ROLE_SURVEYOR

        missing: list[str] = []
        if quarry is None:
            missing.append("выберите карьер")
        elif not allowed:
            missing.append("нужна роль surveyor на этом карьере")
        if not self._passport_combo.currentData():
            missing.append("нужен утверждённый/активный паспорт со взрывом")
        if not self._device_combo.currentData() or not self._calibration_combo.currentData():
            missing.append("зарегистрируйте ZED (или тестовое устройство)")
        if self._last_frame is None and not self._series:
            missing.append("запустите превью камеры или добавьте кадры с диска")

        self._capture_button.setText(
            f"Отправить серию на анализ ({len(self._series)})" if self._series
            else "Снять и отправить на анализ"
        )
        ready = not missing
        self._capture_button.setEnabled(ready)
        if ready:
            text = "Готово к съёмке — кадр уйдёт на анализ"
            # Стерео-кадр + тестовое устройство = заглушечная калибровка: реальный
            # CV-контур честно упадёт. Предупреждаем заранее, не блокируя mock-тесты.
            device = self._selected_device()
            if (
                self._last_frame is not None
                and self._last_frame.side_by_side
                and device is not None
                and device.serial_number.startswith("TEST-")
            ):
                text += (
                    " · выбрано тестовое устройство — для реального анализа "
                    "зарегистрируйте ZED (заводская калибровка)"
                )
            self._ready_label.setText(text)
            self._ready_label.setStyleSheet("color: #1f6b3a;")
            self._set_status("ok", text)
            self._capture_button.setToolTip("")
        else:
            text = "Для съёмки: " + " · ".join(missing)
            self._ready_label.setText(text)
            self._ready_label.setStyleSheet("color: #7b5100;")
            if self._last_frame is None and not self._series:
                self._set_status("warning", "Камера не выбрана или превью ещё не запущено.")
            else:
                self._set_status("warning", text)
            self._capture_button.setToolTip(text)

    def _selected_device(self) -> Device | None:
        index = self._device_combo.currentIndex()
        if 0 <= index < len(self._devices):
            return self._devices[index]
        return None

    # --- Preview ----------------------------------------------------------------------

    def _toggle_preview(self) -> None:
        if self._preview_worker is not None:
            self._stop_preview()
            return
        index = self._camera_combo.currentData()
        if index is None or index < 0:
            self._show_error("Камера не выбрана")
            return
        self._start_preview(index)

    def _maybe_autostart_preview(self) -> None:
        index = self._camera_combo.currentData()
        if self.isVisible() and self._preview_worker is None and index is not None and index >= 0:
            self._start_preview(index)

    def _start_preview(self, index: int) -> None:
        worker = _PreviewWorker(index)
        worker.signals.frame.connect(self._on_preview_frame)
        worker.signals.error.connect(self._on_preview_error)
        worker.signals.stopped.connect(self._on_preview_stopped)
        self._preview_worker = worker  # keep alive while running
        QThreadPool.globalInstance().start(worker)
        self._preview_button.setText("Стоп превью")
        self._set_status("neutral", "Запускаю превью камеры.")

    def _stop_preview(self) -> None:
        if self._preview_worker is not None:
            self._preview_worker.stop()

    def _on_preview_stopped(self) -> None:
        self._preview_worker = None
        self._preview_button.setText("Старт превью")
        self._last_preview_pixmap = None
        self._preview_label.clear()
        self._preview_label.setText("Превью выключено")
        if self.isVisible():
            self._set_status("warning", "Превью остановлено.")

    def _on_preview_error(self, message: str) -> None:
        self._show_error(message)

    def _on_preview_frame(self, frame: StereoFrame) -> None:
        self._last_frame = frame
        self._mode_label.setText(
            f"стерео SBS, {frame.width}×{frame.height} на глаз" if frame.side_by_side
            else f"моно, {frame.width}×{frame.height} (только left_frame)"
        )
        self._clear_error()
        self._set_status(
            "neutral",
            "Камера работает: "
            + (
                f"стерео SBS, {frame.width}×{frame.height} на глаз"
                if frame.side_by_side
                else f"моно, {frame.width}×{frame.height}"
            ),
        )
        # The left eye is a slice of the SBS frame (non-contiguous view) and
        # QImage requires a C-contiguous buffer; this also serves as the copy
        # (the ndarray buffer is reused by the next frame).
        left = np.ascontiguousarray(frame.left)
        image = QImage(
            left.data, left.shape[1], left.shape[0], left.strides[0],
            QImage.Format.Format_BGR888,
        ).copy()
        self._last_preview_pixmap = QPixmap.fromImage(image)
        self._render_preview_pixmap()
        self._apply_role_gating()

    def _render_preview_pixmap(self) -> None:
        if self._last_preview_pixmap is None:
            return
        size = self._preview_label.size()
        if size.width() <= 1 or size.height() <= 1:
            return
        self._preview_label.setPixmap(
            self._last_preview_pixmap.scaled(
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    # --- Series management (CAP-MULTI) ----------------------------------------------------

    def _add_current_to_series(self) -> None:
        frame = self._last_frame
        if frame is None:
            self._show_error("Камера не открыта. Выберите камеру и запустите превью.")
            return
        left = np.ascontiguousarray(frame.left)
        entry = {
            "left_jpg": encode_jpeg(left),
            "right_jpg": encode_jpeg(np.ascontiguousarray(frame.right))
            if frame.right is not None else None,
            "stereo": frame.side_by_side,
        }
        self._append_series_entry(entry, left)

    def _load_from_disk(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Кадры с диска", "", "Изображения (*.jpg *.jpeg *.png)"
        )
        if not paths:
            return
        import cv2

        from zmetrics_desktop.capture.stereo import split_side_by_side

        errors: list[str] = []
        for path in paths:
            image = cv2.imread(path, cv2.IMREAD_COLOR)
            if image is None:
                errors.append(path)
                continue
            frame = split_side_by_side(image)
            entry = {
                "left_jpg": encode_jpeg(np.ascontiguousarray(frame.left)),
                "right_jpg": encode_jpeg(np.ascontiguousarray(frame.right))
                if frame.right is not None else None,
                "stereo": frame.side_by_side,
            }
            self._append_series_entry(entry, np.ascontiguousarray(frame.left))
        if errors:
            self._show_error("Не прочитан файл: " + "; ".join(errors))

    def _append_series_entry(self, entry: dict, left_bgr: np.ndarray) -> None:
        self._series.append(entry)
        image = QImage(
            left_bgr.data, left_bgr.shape[1], left_bgr.shape[0], left_bgr.strides[0],
            QImage.Format.Format_BGR888,
        ).copy()
        icon = QIcon(QPixmap.fromImage(image).scaled(
            96, 60, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
        kind = "стерео" if entry["stereo"] else "моно"
        item = QListWidgetItem(icon, f"{len(self._series) - 1}: {kind}")
        self._series_list.addItem(item)
        self._apply_role_gating()

    def _remove_selected_shot(self) -> None:
        row = self._series_list.currentRow()
        if 0 <= row < len(self._series):
            self._series.pop(row)
            self._series_list.takeItem(row)
            self._relabel_series()
            self._apply_role_gating()

    def _clear_series(self) -> None:
        self._series.clear()
        self._series_list.clear()
        self._apply_role_gating()

    def _relabel_series(self) -> None:
        for row in range(self._series_list.count()):
            kind = "стерео" if self._series[row]["stereo"] else "моно"
            self._series_list.item(row).setText(f"{row}: {kind}")

    # --- Capture & send ------------------------------------------------------------------

    def _capture_and_send(self) -> None:
        quarry = self._state.quarry
        passport_id = self._passport_combo.currentData()
        device_id = self._device_combo.currentData()
        calibration_id = self._calibration_combo.currentData()
        if quarry is None:
            return
        if not passport_id:
            self._show_error("Выберите паспорт с зафиксированным взрывом")
            return
        if not device_id or not calibration_id:
            self._show_error(
                "Нет устройства/калибровки — нажмите «Подготовить тестовое устройство»"
            )
            return

        # Серия, если она набрана; иначе одиночный текущий кадр (как раньше)
        if self._series:
            entries = list(self._series)
        elif self._last_frame is not None:
            frame = self._last_frame
            entries = [{
                "left_jpg": encode_jpeg(np.ascontiguousarray(frame.left)),
                "right_jpg": encode_jpeg(np.ascontiguousarray(frame.right))
                if frame.right is not None else None,
                "stereo": frame.side_by_side,
            }]
        else:
            return

        self._clear_error()
        self._capture_button.setEnabled(False)
        self._result_labels["job"].setText("отправка…")
        self._set_status("neutral", "Отправляю кадры на анализ.")

        context = self._context

        def send() -> tuple[str, list[str]] | str:
            frames_dir = context.settings.offline_db_path.parent / "frames"
            frames_dir.mkdir(parents=True, exist_ok=True)
            frames: list[dict] = []
            for entry in entries:
                stem = uuid.uuid4().hex
                left_path = frames_dir / f"{stem}_left.jpg"
                left_path.write_bytes(entry["left_jpg"])
                right_path = None
                if entry["right_jpg"] is not None:
                    right_path = frames_dir / f"{stem}_right.jpg"
                    right_path.write_bytes(entry["right_jpg"])
                frames.append({
                    "left_path": str(left_path),
                    "right_path": str(right_path) if right_path else None,
                })

            payload = build_series_payload(
                quarry_id=quarry.id,
                passport_id=passport_id,
                device_id=device_id,
                calibration_id=calibration_id,
                frames=frames,
            )
            if context.api.is_reachable():
                return perform_capture_upload(context.api, payload)
            queue = context.make_sync_manager()  # per-thread sqlite connection
            try:
                queue.enqueue(KIND_CAPTURE_UPLOAD, payload)
            finally:
                queue.close()
            return "queued"

        submit(send, self._on_sent, self._on_send_error)

    def _on_sent(self, outcome: object) -> None:
        self._clear_series()
        self._apply_role_gating()
        if outcome == "queued":
            self._result_labels["job"].setText(
                "Оффлайн — съёмка в очереди, отправится автоматически"
            )
            self._set_status("warning", "Сервер недоступен: съёмка сохранена в очереди.")
            return
        session_id, job_ids = outcome  # type: ignore[misc]
        self._job_ref = (session_id, list(job_ids))
        self._poll_count = 0
        self._result_labels["job"].setText("в очереди")
        self._set_status("ok", "Кадры отправлены, анализ поставлен в очередь.")
        self._poll_timer.start()

    def _on_send_error(self, message: str) -> None:
        self._apply_role_gating()
        self._result_labels["job"].setText("—")
        self._show_error(message)

    # --- Job polling ------------------------------------------------------------------------

    def _poll_job(self) -> None:
        ref = self._job_ref
        if ref is None:
            self._poll_timer.stop()
            return
        self._poll_count += 1
        if self._poll_count > JOB_POLL_LIMIT:
            self._poll_timer.stop()
            self._result_labels["job"].setText(
                "долго выполняется — результат появится в «Отчётах»"
            )
            return
        session_id, _job_ids = ref
        submit(
            lambda: self._api.list_jobs(session_id),
            self._on_jobs_status,
            self._on_send_error,
        )

    def _on_jobs_status(self, jobs: list[AnalysisJob]) -> None:
        if self._job_ref is None:
            return
        session_id, job_ids = self._job_ref
        wanted = set(job_ids)
        ours = [j for j in jobs if j.id in wanted]
        if not ours:
            return
        completed = [j for j in ours if j.status == "completed"]
        failed = [j for j in ours if j.status == "failed"]

        if len(ours) == 1:
            status = ours[0].status
            self._result_labels["job"].setText(JOB_STATUS_RU.get(status, status))
        else:
            text = f"серия: завершено {len(completed)}/{len(ours)}"
            if failed:
                text += f", ошибок {len(failed)}"
            self._result_labels["job"].setText(text)

        if len(completed) + len(failed) < len(ours):
            return  # ещё выполняется

        self._poll_timer.stop()
        self._job_ref = None
        self._load_summary()

        if failed and not completed:
            self._show_error(
                failed[0].error_message or "Пайплайн завершился с ошибкой"
            )
            return
        if failed:
            self._show_error(
                f"Часть кадров завершилась с ошибкой: {len(failed)} из {len(ours)}"
            )

        ordered = sorted(completed, key=lambda j: j.frame_index)

        def fetch_results() -> list[tuple[int, AnalysisResult]]:
            return [
                (job.frame_index, self._api.get_job_result(session_id, job.id))
                for job in ordered
            ]

        submit(fetch_results, self._on_results, self._show_error)

    def _on_results(self, indexed: list[tuple[int, AnalysisResult]]) -> None:
        if not indexed:
            return
        labels = self._result_labels
        _first_index, first = indexed[0]
        labels["p10"].setText(_fmt(first.p10_mm, " мм"))
        labels["p50"].setText(_fmt(first.p50_mm, " мм"))
        labels["p80"].setText(_fmt(first.p80_mm, " мм"))
        labels["confidence"].setText(_fmt(first.confidence_score))
        notes = _fmt(first.confidence_notes)
        if len(indexed) > 1:
            per_frame = " · ".join(
                f"кадр {idx}: P80 {_fmt(res.p80_mm, ' мм')}" for idx, res in indexed
            )
            notes = f"{per_frame}\n{notes}"
        labels["notes"].setText(notes)
        self._set_status("ok", "Анализ завершён, результат обновлён.")

    # --- Blast photo list (capture summary) ---------------------------------------------------

    def _load_summary(self) -> None:
        quarry = self._state.quarry
        passport_id = self._passport_combo.currentData()
        if quarry is None or not passport_id:
            self._summary_label.setText("—")
            return

        def fetch() -> list[CaptureSessionSummary]:
            try:
                return self._api.get_capture_summary(quarry.id, passport_id)
            except ApiError as exc:
                if exc.status_code == 404:  # взрыва ещё нет — снимков нет
                    return []
                raise

        submit(fetch, self._on_summary, self._show_error)

    def _on_summary(self, sessions: list[CaptureSessionSummary]) -> None:
        if not sessions:
            self._summary_label.setText("Снимков пока нет")
            return
        lines: list[str] = []
        for session in sessions:
            when = session.capture_datetime[:16].replace("T", " ")
            who = session.captured_by_name or "—"
            frames_bits: list[str] = []
            for frame in session.frames:
                kind = "стерео" if frame.has_right else ("моно" if frame.has_left else "?")
                status = JOB_STATUS_RU.get(frame.job_status or "", frame.job_status or "нет анализа")
                frames_bits.append(f"кадр {frame.frame_index}: {kind} · {status}")
            jobs = f"✓{session.jobs_completed}" + (
                f" ✗{session.jobs_failed}" if session.jobs_failed else ""
            )
            lines.append(
                f"<b>{when}</b> · {who} · кадров: {session.frame_count} · анализы: {jobs}"
                + ("<br>&nbsp;&nbsp;" + "; ".join(frames_bits) if frames_bits else "")
            )
        self._summary_label.setText("<br>".join(lines))

    # --- ZED registration -----------------------------------------------------------------

    def _register_zed(self) -> None:
        """Качает заводскую калибровку по серийнику и регистрирует Device + Calibration."""
        prefill = next(
            (d.serial_number for d in self._devices if "zed" in d.model.lower()), ""
        )
        serial, ok = QInputDialog.getText(
            self,
            "Регистрация ZED",
            "Серийный номер камеры (на наклейке, например 21907252):",
            text=prefill,
        )
        serial = serial.strip()
        if not ok or not serial:
            return

        # Разрешение калибровки — по текущему стерео-кадру; без превью считаем 2K (2.2K SBS)
        resolution = "2K"
        frame = self._last_frame
        if frame is not None and frame.side_by_side:
            try:
                resolution = resolution_for_frame(frame.width, frame.height)
            except ZedConfError:
                pass

        self._clear_error()
        self._register_zed_button.setEnabled(False)
        self._register_zed_button.setText("Скачиваю калибровку…")
        self._set_status("neutral", "Скачиваю заводскую калибровку ZED.")

        def register() -> str:
            payload = build_calibration_payload(
                parse_zed_conf(fetch_conf_text(serial)), resolution
            )
            try:
                device = self._api.create_device({
                    "serial_number": serial,
                    "model": "ZED 2",
                    "notes": f"Заводская калибровка calib.stereolabs.com ({resolution})",
                })
            except ApiError as exc:
                if exc.status_code != 409:  # 409 — серийник уже зарегистрирован
                    raise
                device = next(
                    d for d in self._api.list_devices() if d.serial_number == serial
                )
            self._api.add_calibration(device.id, payload)
            return serial

        def done(registered: object) -> None:
            self._register_zed_button.setEnabled(True)
            self._register_zed_button.setText("Зарегистрировать ZED")
            self._select_device_serial = str(registered)
            self._set_status("ok", "ZED зарегистрирована, обновляю список устройств.")
            self._load_devices()

        def failed(message: str) -> None:
            self._register_zed_button.setEnabled(True)
            self._register_zed_button.setText("Зарегистрировать ZED")
            self._show_error(f"Не удалось зарегистрировать ZED: {message}")

        submit(register, done, failed)

    # --- Test device helper -------------------------------------------------------------------

    def _prepare_test_device(self) -> None:
        """Регистрирует камеру как Device + калибровку-заглушку (тест без ZED 2)."""
        camera_name = self._camera_combo.currentText() or "Webcam"
        frame = self._last_frame
        width = frame.width if frame else 1280
        height = frame.height if frame else 720
        self._prepare_button.setEnabled(False)

        def prepare() -> None:
            device = self._api.create_device({
                "serial_number": f"TEST-{uuid.uuid4().hex[:8].upper()}",
                "model": camera_name,
                "notes": "Тестовая веб-камера; калибровка-заглушка — только mock-пайплайн",
            })
            self._api.add_calibration(device.id, {
                "left_camera_matrix": _STUB_MATRIX,
                "right_camera_matrix": _STUB_MATRIX,
                "left_dist_coeffs": _STUB_DIST,
                "right_dist_coeffs": _STUB_DIST,
                "rotation_matrix": _STUB_MATRIX,
                "translation_vector": {"rows": 3, "cols": 1, "data": [120.0, 0.0, 0.0]},
                "baseline_mm": 120.0,
                "image_width_px": width,
                "image_height_px": height,
            })

        def done(_result: object) -> None:
            self._prepare_button.setEnabled(True)
            self._load_devices()

        def failed(message: str) -> None:
            self._prepare_button.setEnabled(True)
            self._show_error(message)

        submit(prepare, done, failed)
