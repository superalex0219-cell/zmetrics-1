"""UVC camera enumeration and capture (ZED 2 as a standard webcam).

The ZED 2 outputs one side-by-side (left|right) frame over UVC, so capture goes through
plain ``cv2.VideoCapture`` — Media Foundation backend on Windows. Device names come from
DirectShow via ``pygrabber``. The capture handle is injectable (``capture_factory``) so
everything here is unit-testable without hardware or OpenCV installed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol, Sequence

from zmetrics_desktop.capture.stereo import StereoFrame, split_side_by_side

# cv2.CAP_PROP_* numeric values (stable OpenCV API) — kept local so this module stays
# importable without OpenCV.
_CAP_PROP_FRAME_WIDTH = 3
_CAP_PROP_FRAME_HEIGHT = 4

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
    """Enumerate video capture devices with their DirectShow names (Windows).

    ``pygrabber`` returns names in the same device order ``cv2.VideoCapture`` uses for
    its integer index, so ``CameraInfo.index`` can be passed straight to ``StereoCamera``.
    """
    from pygrabber.dshow_graph import FilterGraph  # lazy: win32-only dependency

    names = FilterGraph().get_input_devices()
    return [CameraInfo(index=i, name=name) for i, name in enumerate(names)]


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

    return cv2.VideoCapture(index, cv2.CAP_MSMF)


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
