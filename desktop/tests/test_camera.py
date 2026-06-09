import numpy as np
import pytest

from zmetrics_desktop.capture.camera import (
    ZED2_SBS_MODES,
    CameraError,
    CameraInfo,
    StereoCamera,
    pick_default_camera,
)

_FALLBACK = (640, 480)  # what a UVC driver reports when the requested mode is unsupported


class FakeSource:
    """cv2.VideoCapture stand-in: accepts only ``supported`` (width, height) modes."""

    def __init__(
        self,
        supported: set[tuple[int, int]] | None = None,
        *,
        opened: bool = True,
        frame_ok: bool = True,
    ) -> None:
        self._supported = supported or set()
        self._opened = opened
        self._frame_ok = frame_ok
        self._requested = list(_FALLBACK)
        self.released = False

    def isOpened(self) -> bool:  # noqa: N802 — cv2 method name
        return self._opened

    def set(self, prop: int, value: float) -> bool:
        if prop == 3:
            self._requested[0] = int(value)
        elif prop == 4:
            self._requested[1] = int(value)
        return True

    def get(self, prop: int) -> float:
        width, height = self._requested
        if (width, height) not in self._supported:
            width, height = _FALLBACK
        return float(width if prop == 3 else height)

    def read(self):
        if not self._frame_ok:
            return False, None
        width = int(self.get(3))
        height = int(self.get(4))
        return True, np.zeros((height, width, 3), dtype=np.uint8)

    def release(self) -> None:
        self.released = True


def _camera(source: FakeSource, **kwargs) -> StereoCamera:
    return StereoCamera(0, capture_factory=lambda index: source, **kwargs)


# --- open() ---------------------------------------------------------------------------


def test_open_picks_first_supported_mode():
    source = FakeSource(supported={(2560, 720), (1344, 376)})
    camera = _camera(source).open()
    # 2.2K and HD1080 are rejected by the driver; HD720 is the first accepted mode.
    assert (camera.width, camera.height) == (2560, 720)


def test_open_falls_back_when_no_mode_supported():
    camera = _camera(FakeSource(supported=set())).open()
    assert (camera.width, camera.height) == _FALLBACK


def test_open_raises_when_camera_unavailable():
    source = FakeSource(opened=False)
    with pytest.raises(CameraError, match="open"):
        _camera(source).open()
    assert source.released  # handle is not leaked


def test_open_honours_custom_mode_list():
    source = FakeSource(supported={(1344, 376), (2560, 720)})
    camera = _camera(source, modes=[(1344, 376)]).open()
    assert (camera.width, camera.height) == (1344, 376)


# --- read() ---------------------------------------------------------------------------


def test_read_splits_side_by_side_frame():
    camera = _camera(FakeSource(supported={(2560, 720)})).open()
    frame = camera.read()
    assert frame.side_by_side
    assert frame.width == 1280
    assert frame.height == 720
    assert frame.left.shape == (720, 1280, 3)
    assert frame.right is not None and frame.right.shape == (720, 1280, 3)


def test_read_before_open_raises():
    with pytest.raises(CameraError, match="not open"):
        _camera(FakeSource()).read()


def test_read_failure_raises():
    camera = _camera(FakeSource(supported={(2560, 720)}, frame_ok=False)).open()
    with pytest.raises(CameraError, match="read"):
        camera.read()


def test_context_manager_releases_source():
    source = FakeSource(supported={(2560, 720)})
    with _camera(source) as camera:
        assert camera.read().side_by_side
    assert source.released


# --- device picking -------------------------------------------------------------------


def test_zed2_modes_are_all_side_by_side():
    assert all(width / height > 1.8 for width, height in ZED2_SBS_MODES)


def test_camera_info_detects_zed_by_name():
    assert CameraInfo(0, "ZED 2 Stereo Camera").looks_like_zed
    assert not CameraInfo(1, "Integrated Webcam").looks_like_zed


def test_pick_default_prefers_zed():
    cameras = [
        CameraInfo(0, "Integrated Webcam"),
        CameraInfo(1, "ZED 2 Stereo Camera"),
    ]
    assert pick_default_camera(cameras).index == 1


def test_pick_default_falls_back_to_first():
    cameras = [CameraInfo(0, "Integrated Webcam")]
    assert pick_default_camera(cameras).index == 0
    assert pick_default_camera([]) is None
