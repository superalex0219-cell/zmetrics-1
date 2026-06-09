"""Side-by-side stereo frame handling.

Mirrors the logic of the former Android ``buildFramePayload``: if a frame's aspect ratio
exceeds a threshold it is treated as a horizontally concatenated stereo pair and split at
the midpoint into left/right halves.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# A frame is treated as side-by-side when width/height exceeds this ratio.
SIDE_BY_SIDE_ASPECT_THRESHOLD = 1.8


@dataclass(frozen=True)
class StereoFrame:
    """A captured frame, split into left/right when it is side-by-side.

    ``right`` is ``None`` for a non-stereo (single-lens) frame. ``width``/``height`` are
    the dimensions of a single eye (i.e. half-width for a side-by-side source).
    """

    left: np.ndarray
    right: np.ndarray | None
    width: int
    height: int
    side_by_side: bool


def split_side_by_side(
    frame: np.ndarray,
    threshold: float = SIDE_BY_SIDE_ASPECT_THRESHOLD,
) -> StereoFrame:
    """Split a side-by-side frame into left/right halves.

    A wide frame (``width / height > threshold``) is split at ``width // 2``; both halves
    have width ``width // 2`` (an odd last column is dropped, matching the Android crop).
    A non-wide frame is returned as ``left`` only with ``right=None``.
    """
    if frame.ndim < 2:
        raise ValueError("frame must be at least 2-D (H, W[, C])")

    height, width = frame.shape[:2]
    if height == 0 or width == 0:
        raise ValueError("frame has a zero dimension")

    is_sbs = (width / height) > threshold
    if not is_sbs:
        return StereoFrame(
            left=frame,
            right=None,
            width=width,
            height=height,
            side_by_side=False,
        )

    half = width // 2
    left = frame[:, :half]
    right = frame[:, half : half * 2]
    return StereoFrame(
        left=left,
        right=right,
        width=half,
        height=height,
        side_by_side=True,
    )


def encode_jpeg(image: np.ndarray, quality: int = 92) -> bytes:
    """Encode a BGR image to JPEG bytes. Imports cv2 lazily (heavy dependency)."""
    import cv2  # local import: keep module importable without OpenCV (e.g. in unit tests)

    ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    if not ok:
        raise RuntimeError("cv2.imencode failed to encode frame to JPEG")
    return buf.tobytes()
