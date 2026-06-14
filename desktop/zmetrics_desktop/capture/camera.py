"""UVC camera enumeration and capture (ZED 2 as a standard webcam).

The ZED 2 outputs one side-by-side (left|right) frame over UVC, so capture goes through
plain ``cv2.VideoCapture`` — Media Foundation backend on Windows, AVFoundation on macOS.
The capture handle is injectable (``capture_factory``) so everything here is unit-testable
without hardware or OpenCV installed.
"""
from __future__ import annotations

import platform
import plistlib
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Protocol, Sequence

from zmetrics_desktop.capture.stereo import StereoFrame, split_side_by_side

# cv2.CAP_PROP_* numeric values (stable OpenCV API) — kept local so this module stays
# importable without OpenCV.
_CAP_PROP_FRAME_WIDTH = 3
_CAP_PROP_FRAME_HEIGHT = 4
_CAP_PROP_FOURCC = 6

# Side-by-side modes the ZED 2 exposes over UVC, preferred first: (width, height).
ZED2_SBS_MODES: list[tuple[int, int]] = [
    (4416, 1242),  # 2.2K
    (3840, 1080),  # HD1080
    (2560, 720),   # HD720
    (1344, 376),   # VGA
]


class CameraError(RuntimeError):
    """Raised when a camera cannot be opened or a frame cannot be read."""


@dataclass(frozen=True)
class CameraInfo:
    """A video capture device: DirectShow name + index usable with cv2.VideoCapture."""

    index: int
    name: str

    @property
    def looks_like_zed(self) -> bool:
        return "zed" in self.name.lower()


def list_cameras() -> list[CameraInfo]:
    """Enumerate video capture devices.

    Windows uses DirectShow names from ``pygrabber``. macOS/Linux fall back to probing
    OpenCV indexes, because OpenCV's Python API does not expose portable device names.
    """
    system = platform.system()
    if system == "Windows":
        return _list_windows_cameras()
    return _list_opencv_cameras(system)


def _list_windows_cameras() -> list[CameraInfo]:
    from pygrabber.dshow_graph import FilterGraph  # lazy: win32-only dependency

    names = FilterGraph().get_input_devices()
    return [CameraInfo(index=i, name=name) for i, name in enumerate(names)]


def _list_opencv_cameras(system: str, *, max_index: int = 10) -> list[CameraInfo]:
    import cv2  # lazy: heavy dependency

    backend = _opencv_backend(cv2, system)
    system_names = _macos_camera_names() if system == "Darwin" else []
    cameras: list[CameraInfo] = []
    for index in range(max_index):
        capture = cv2.VideoCapture(index, backend)
        try:
            if not capture.isOpened():
                continue
            name = system_names[index] if index < len(system_names) else f"Camera #{index}"
            cameras.append(CameraInfo(index=index, name=name))
        finally:
            capture.release()
    return cameras


def _macos_camera_names() -> list[str]:
    """Best-effort camera names in the order macOS reports them."""
    try:
        result = subprocess.run(
            ["system_profiler", "SPCameraDataType", "-xml"],
            check=False,
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0 or not result.stdout:
        return []
    try:
        payload = plistlib.loads(result.stdout)
    except plistlib.InvalidFileException:
        return []

    names: list[str] = []
    for section in payload:
        for item in section.get("_items", []):
            name = item.get("_name")
            if isinstance(name, str) and name:
                names.append(name)
    return names


def pick_default_camera(cameras: Sequence[CameraInfo]) -> CameraInfo | None:
    """Prefer a ZED device; otherwise the first camera; ``None`` when there are none."""
    for camera in cameras:
        if camera.looks_like_zed:
            return camera
    return cameras[0] if cameras else None


class FrameSource(Protocol):
    """The subset of the cv2.VideoCapture interface StereoCamera relies on."""

    def isOpened(self) -> bool: ...  # noqa: N802 — cv2 method name
    def set(self, prop: int, value: float) -> bool: ...
    def get(self, prop: int) -> float: ...
    def read(self) -> tuple[bool, Any]: ...
    def release(self) -> None: ...


CaptureFactory = Callable[[int], FrameSource]


def _default_capture_factory(index: int) -> FrameSource:
    import cv2  # lazy: heavy dependency

    return cv2.VideoCapture(index, _opencv_backend(cv2, platform.system()))


def _opencv_backend(cv2: Any, system: str) -> int:
    if system == "Windows":
        return cv2.CAP_MSMF
    if system == "Darwin":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY


class StereoCamera:
    """A UVC camera opened at the best supported full side-by-side resolution.

    Usage::

        with StereoCamera(info.index) as camera:
            frame = camera.read()   # StereoFrame with left/right halves

    ``open()`` walks ``modes`` in order and keeps the first one the driver actually
    accepts (UVC silently falls back when a mode is unsupported, so the requested size
    is read back and compared).
    """

    def __init__(
        self,
        index: int,
        *,
        modes: Sequence[tuple[int, int]] | None = None,
        capture_factory: CaptureFactory | None = None,
    ) -> None:
        self._index = index
        self._modes = list(modes) if modes is not None else list(ZED2_SBS_MODES)
        self._factory = capture_factory or _default_capture_factory
        self._source: FrameSource | None = None
        self.width = 0
        self.height = 0

    def open(self) -> "StereoCamera":
        source = self._factory(self._index)
        if not source.isOpened():
            source.release()
            raise CameraError(f"Cannot open camera #{self._index}")

        for width, height in self._modes:
            _request_mjpg(source)
            source.set(_CAP_PROP_FRAME_WIDTH, width)
            source.set(_CAP_PROP_FRAME_HEIGHT, height)
            actual = (
                int(source.get(_CAP_PROP_FRAME_WIDTH)),
                int(source.get(_CAP_PROP_FRAME_HEIGHT)),
            )
            if actual == (width, height):
                break

        self.width = int(source.get(_CAP_PROP_FRAME_WIDTH))
        self.height = int(source.get(_CAP_PROP_FRAME_HEIGHT))
        self._source = source
        return self

    def read(self) -> StereoFrame:
        """Grab one frame and split it into left/right when it is side-by-side."""
        if self._source is None:
            raise CameraError("Camera is not open — call open() first")
        ok, frame = self._source.read()
        if not ok or frame is None:
            raise CameraError("Failed to read a frame from the camera")
        return split_side_by_side(frame)

    def close(self) -> None:
        if self._source is not None:
            self._source.release()
            self._source = None

    def __enter__(self) -> "StereoCamera":
        return self.open()

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def _request_mjpg(source: FrameSource) -> None:
    """Ask UVC devices for MJPG before high-res modes; ignored when unsupported."""
    try:
        import cv2

        source.set(_CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    except Exception:
        return
