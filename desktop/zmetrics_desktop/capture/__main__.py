"""Manual smoke test: ``python -m zmetrics_desktop.capture``.

Lists cameras, opens the default one (ZED preferred, otherwise the first — e.g. a laptop
webcam), grabs one frame, splits it if side-by-side, and writes JPEG(s) next to the
current directory. No backend required.
"""
from __future__ import annotations

from pathlib import Path

from zmetrics_desktop.capture.camera import StereoCamera, list_cameras, pick_default_camera
from zmetrics_desktop.capture.stereo import encode_jpeg


def main() -> int:
    cameras = list_cameras()
    if not cameras:
        print("Камеры не найдены")
        return 1

    for camera in cameras:
        marker = "  <- ZED" if camera.looks_like_zed else ""
        print(f"[{camera.index}] {camera.name}{marker}")

    chosen = pick_default_camera(cameras)
    assert chosen is not None
    print(f"\nОткрываю [{chosen.index}] {chosen.name} ...")

    with StereoCamera(chosen.index) as camera:
        print(f"Режим: {camera.width}x{camera.height}")
        frame = camera.read()

    out_dir = Path.cwd()
    if frame.side_by_side:
        assert frame.right is not None
        (out_dir / "smoke_left.jpg").write_bytes(encode_jpeg(frame.left))
        (out_dir / "smoke_right.jpg").write_bytes(encode_jpeg(frame.right))
        print(f"SBS-кадр {frame.width}x{frame.height} на глаз -> smoke_left.jpg + smoke_right.jpg")
    else:
        (out_dir / "smoke_left.jpg").write_bytes(encode_jpeg(frame.left))
        print(f"Моно-кадр {frame.width}x{frame.height} -> smoke_left.jpg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
