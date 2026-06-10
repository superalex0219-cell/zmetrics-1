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

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QHideEvent, QImage, QPixmap, QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
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
from zmetrics_desktop.models import AnalysisResult, BlastPassport, Calibration, Device, Quarry
from zmetrics_desktop.offline.capture_upload import (
    KIND_CAPTURE_UPLOAD,
    build_payload,
    perform_capture_upload,
)
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
        self._preview_worker: _PreviewWorker | None = None
        self._job_ref: tuple[str, str] | None = None  # (session_id, job_id)
        self._poll_count = 0

        root = QVBoxLayout(self)

        # --- Context selectors -----------------------------------------------------
        selectors = QFormLayout()
        self._passport_combo = QComboBox()
        selectors.addRow("Паспорт (утв./активный):", self._passport_combo)
        device_row = QHBoxLayout()
        self._device_combo = QComboBox()
        self._device_combo.currentIndexChanged.connect(self._on_device_selected)
        device_row.addWidget(self._device_combo, stretch=1)
        self._calibration_combo = QComboBox()
        device_row.addWidget(self._calibration_combo, stretch=1)
        self._register_zed_button = QPushButton("Зарегистрировать ZED")
        self._register_zed_button.setToolTip(
            "Скачивает заводскую калибровку с calib.stereolabs.com по серийному\n"
            "номеру (на наклейке камеры) и регистрирует устройство + калибровку."
        )
        self._register_zed_button.clicked.connect(self._register_zed)
        device_row.addWidget(self._register_zed_button)
        self._prepare_button = QPushButton("Подготовить тестовое устройство")
        self._prepare_button.setToolTip(
            "Регистрирует выбранную камеру как Device и создаёт калибровку-заглушку.\n"
            "Только для тестов без ZED 2 — реальное стерео с ней не считается."
        )
        self._prepare_button.clicked.connect(self._prepare_test_device)
        device_row.addWidget(self._prepare_button)
        selectors.addRow("Устройство / калибровка:", device_row)
        root.addLayout(selectors)

        # --- Camera + preview --------------------------------------------------------
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
        root.addLayout(camera_row)

        body = QHBoxLayout()
        self._preview_label = QLabel("Превью выключено")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setMinimumSize(480, 300)
        self._preview_label.setStyleSheet("background: #222; color: #888;")
        body.addWidget(self._preview_label, stretch=3)
        body.addWidget(self._build_result_panel(), stretch=2)
        root.addLayout(body, stretch=1)

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
        self._error_label.setStyleSheet("color: #b00;")
        self._error_label.setWordWrap(True)
        actions.addWidget(self._error_label, stretch=1)
        root.addLayout(actions)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(JOB_POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll_job)

        self._state.quarry_changed.connect(self._on_state_quarry_changed)
        self._state.access_changed.connect(self._apply_role_gating)
        self._passport_combo.currentIndexChanged.connect(lambda *_: self._apply_role_gating())
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

    def refresh(self) -> None:
        self._error_label.clear()
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

        submit(list_safe, self._on_cameras, self._error_label.setText)

    def _on_cameras(self, cameras: list[CameraInfo]) -> None:
        self._cameras = cameras
        self._camera_combo.clear()
        for camera in cameras:
            label = camera.name + (" (ZED)" if camera.looks_like_zed else "")
            self._camera_combo.addItem(label, camera.index)
        if not cameras:
            self._camera_combo.addItem("Камеры не найдены", -1)
            return
        # ZED — приоритетный выбор; превью включаем сразу, без лишнего клика
        zed_idx = next((i for i, c in enumerate(cameras) if c.looks_like_zed), None)
        if zed_idx is not None:
            self._camera_combo.setCurrentIndex(zed_idx)
        self._maybe_autostart_preview()

    def _load_passports(self, quarry: Quarry) -> None:
        submit(
            lambda: self._api.list_passports(quarry.id),
            self._on_passports,
            self._error_label.setText,
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
        submit(self._api.list_devices, self._on_devices, self._error_label.setText)

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
            self._error_label.setText,
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
        if self._last_frame is None:
            missing.append("запустите превью камеры")

        ready = not missing
        self._capture_button.setEnabled(ready)
        if ready:
            self._ready_label.setText("✅ Готово к съёмке — кадр уйдёт на анализ")
            self._ready_label.setStyleSheet("color: #2a7;")
            self._capture_button.setToolTip("")
        else:
            text = "Для съёмки: " + " · ".join(missing)
            self._ready_label.setText(text)
            self._ready_label.setStyleSheet("color: #c80;")
            self._capture_button.setToolTip(text)

    # --- Preview ----------------------------------------------------------------------

    def _toggle_preview(self) -> None:
        if self._preview_worker is not None:
            self._stop_preview()
            return
        index = self._camera_combo.currentData()
        if index is None or index < 0:
            self._error_label.setText("Камера не выбрана")
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

    def _stop_preview(self) -> None:
        if self._preview_worker is not None:
            self._preview_worker.stop()

    def _on_preview_stopped(self) -> None:
        self._preview_worker = None
        self._preview_button.setText("Старт превью")
        self._preview_label.setText("Превью выключено")

    def _on_preview_error(self, message: str) -> None:
        self._error_label.setText(message)

    def _on_preview_frame(self, frame: StereoFrame) -> None:
        self._last_frame = frame
        self._mode_label.setText(
            f"стерео SBS, {frame.width}×{frame.height} на глаз" if frame.side_by_side
            else f"моно, {frame.width}×{frame.height} (только left_frame)"
        )
        # The left eye is a slice of the SBS frame (non-contiguous view) and
        # QImage requires a C-contiguous buffer; this also serves as the copy
        # (the ndarray buffer is reused by the next frame).
        left = np.ascontiguousarray(frame.left)
        image = QImage(
            left.data, left.shape[1], left.shape[0], left.strides[0],
            QImage.Format.Format_BGR888,
        ).copy()
        self._preview_label.setPixmap(
            QPixmap.fromImage(image).scaled(
                self._preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self._apply_role_gating()

    # --- Capture & send ------------------------------------------------------------------

    def _capture_and_send(self) -> None:
        frame = self._last_frame
        quarry = self._state.quarry
        passport_id = self._passport_combo.currentData()
        device_id = self._device_combo.currentData()
        calibration_id = self._calibration_combo.currentData()
        if frame is None or quarry is None:
            return
        if not passport_id:
            self._error_label.setText("Выберите паспорт с зафиксированным взрывом")
            return
        if not device_id or not calibration_id:
            self._error_label.setText(
                "Нет устройства/калибровки — нажмите «Подготовить тестовое устройство»"
            )
            return
        self._error_label.clear()
        self._capture_button.setEnabled(False)
        self._result_labels["job"].setText("отправка…")

        context = self._context

        def send() -> tuple[str, str] | str:
            frames_dir = context.settings.offline_db_path.parent / "frames"
            frames_dir.mkdir(parents=True, exist_ok=True)
            stem = uuid.uuid4().hex
            left_path = frames_dir / f"{stem}_left.jpg"
            left_path.write_bytes(encode_jpeg(frame.left))
            right_path = None
            if frame.right is not None:
                right_path = frames_dir / f"{stem}_right.jpg"
                right_path.write_bytes(encode_jpeg(frame.right))

            payload = build_payload(
                quarry_id=quarry.id,
                passport_id=passport_id,
                device_id=device_id,
                calibration_id=calibration_id,
                left_path=str(left_path),
                right_path=str(right_path) if right_path else None,
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
        self._apply_role_gating()
        if outcome == "queued":
            self._result_labels["job"].setText(
                "⚠ Оффлайн — съёмка в очереди, отправится автоматически"
            )
            return
        session_id, job_id = outcome  # type: ignore[misc]
        self._job_ref = (session_id, job_id)
        self._poll_count = 0
        self._result_labels["job"].setText("в очереди")
        self._poll_timer.start()

    def _on_send_error(self, message: str) -> None:
        self._apply_role_gating()
        self._result_labels["job"].setText("—")
        self._error_label.setText(message)

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
        session_id, job_id = ref
        submit(
            lambda: self._api.get_job(session_id, job_id),
            self._on_job_status,
            self._on_send_error,
        )

    def _on_job_status(self, job: object) -> None:
        if self._job_ref is None:
            return
        status = job.status  # type: ignore[attr-defined]
        self._result_labels["job"].setText(JOB_STATUS_RU.get(status, status))
        if status == "failed":
            self._poll_timer.stop()
            self._job_ref = None
            self._error_label.setText(job.error_message or "Пайплайн завершился с ошибкой")  # type: ignore[attr-defined]
        elif status == "completed":
            self._poll_timer.stop()
            session_id, job_id = self._job_ref
            self._job_ref = None
            submit(
                lambda: self._api.get_job_result(session_id, job_id),
                self._on_result,
                self._error_label.setText,
            )

    def _on_result(self, result: AnalysisResult) -> None:
        labels = self._result_labels
        labels["p10"].setText(_fmt(result.p10_mm, " мм"))
        labels["p50"].setText(_fmt(result.p50_mm, " мм"))
        labels["p80"].setText(_fmt(result.p80_mm, " мм"))
        labels["confidence"].setText(_fmt(result.confidence_score))
        labels["notes"].setText(_fmt(result.confidence_notes))

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

        self._error_label.clear()
        self._register_zed_button.setEnabled(False)
        self._register_zed_button.setText("Скачиваю калибровку…")

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
            self._load_devices()

        def failed(message: str) -> None:
            self._register_zed_button.setEnabled(True)
            self._register_zed_button.setText("Зарегистрировать ZED")
            self._error_label.setText(f"Не удалось зарегистрировать ZED: {message}")

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
            self._error_label.setText(message)

        submit(prepare, done, failed)
