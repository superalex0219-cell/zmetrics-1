"""ZED factory calibration: .conf file → backend CalibrationCreate payload.

Stereolabs ships a factory calibration per camera serial, downloadable as an INI
file from ``https://calib.stereolabs.com/?SN=<serial>``. This module parses it and
builds the JSON payload for ``POST /devices/{id}/calibrations`` in the structure
the worker's real stereo pipeline expects (``cv_calibration``/``cv_rectification``):
camera matrices as ``{fx, fy, cx, cy}``, distortion as ``{k1, k2, p1, p2, k3}``,
``R = Rodrigues([RX, CV, RZ])`` and ``T = [-Baseline, TY, TZ]`` in millimeters —
the sign convention of the Stereolabs zed-opencv-native reference.

Pure numpy — no OpenCV dependency, so it is unit-testable anywhere.
"""
from __future__ import annotations

import configparser
import math

import numpy as np

CALIBRATION_URL_TEMPLATE = "https://calib.stereolabs.com/?SN={serial}"

# conf section suffix → per-eye image size (width, height) of the split frame.
# The ZED 2 SBS modes in camera.py are exactly twice these widths.
RESOLUTIONS: dict[str, tuple[int, int]] = {
    "2K": (2208, 1242),
    "FHD": (1920, 1080),
    "HD": (1280, 720),
    "VGA": (672, 376),
}


class ZedConfError(ValueError):
    """Raised when the conf file misses a section or key we need."""


def fetch_conf_text(serial: str, timeout_s: float = 30.0) -> str:
    """Download the factory calibration .conf for a serial from Stereolabs."""
    import httpx  # local import: keep the module importable without httpx

    url = CALIBRATION_URL_TEMPLATE.format(serial=serial.strip())
    resp = httpx.get(url, follow_redirects=True, timeout=timeout_s)
    resp.raise_for_status()
    if "[STEREO]" not in resp.text:
        raise ZedConfError(f"Unexpected response from {url} — not a ZED conf file")
    return resp.text


def resolution_for_frame(width: int, height: int) -> str:
    """Map a per-eye frame size to the conf section suffix (e.g. 2208x1242 → '2K')."""
    for name, size in RESOLUTIONS.items():
        if size == (width, height):
            return name
    raise ZedConfError(f"No ZED calibration resolution for frame {width}x{height}")


def parse_zed_conf(text: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read_string(text)
    return parser


def _camera_dict(conf: configparser.ConfigParser, section: str) -> dict[str, float]:
    if not conf.has_section(section):
        raise ZedConfError(f"Missing section [{section}] in ZED conf")
    cam = conf[section]
    try:
        return {
            "fx": cam.getfloat("fx"),
            "fy": cam.getfloat("fy"),
            "cx": cam.getfloat("cx"),
            "cy": cam.getfloat("cy"),
        }
    except (configparser.NoOptionError, TypeError) as exc:
        raise ZedConfError(f"Incomplete intrinsics in [{section}]: {exc}") from exc


def _dist_dict(conf: configparser.ConfigParser, section: str) -> dict[str, float]:
    cam = conf[section]
    return {
        "k1": cam.getfloat("k1", 0.0),
        "k2": cam.getfloat("k2", 0.0),
        "p1": cam.getfloat("p1", 0.0),
        "p2": cam.getfloat("p2", 0.0),
        "k3": cam.getfloat("k3", 0.0),
    }


def _stereo_value(stereo: configparser.SectionProxy, key: str, resolution: str) -> float:
    """Read a [STEREO] value that may or may not be suffixed with the resolution.

    Newer conf files have plain ``TY``/``TZ``; older ones ``TY_2K``/``TZ_2K``.
    Rotation values (``RX``/``CV``/``RZ``) are always suffixed.
    """
    for candidate in (f"{key}_{resolution}", key):
        value = stereo.getfloat(candidate, fallback=None)
        if value is not None:
            return value
    raise ZedConfError(f"Missing [STEREO] key {key} (or {key}_{resolution})")


def rotation_vector_to_matrix(rvec: np.ndarray) -> np.ndarray:
    """Rodrigues formula: rotation vector (3,) → rotation matrix (3, 3)."""
    theta = float(np.linalg.norm(rvec))
    if theta < 1e-12:
        return np.eye(3)
    k = rvec / theta
    K = np.array(
        [
            [0.0, -k[2], k[1]],
            [k[2], 0.0, -k[0]],
            [-k[1], k[0], 0.0],
        ]
    )
    return np.eye(3) + math.sin(theta) * K + (1.0 - math.cos(theta)) * (K @ K)


def build_calibration_payload(
    conf: configparser.ConfigParser, resolution: str = "2K"
) -> dict:
    """Build the CalibrationCreate body for one resolution section of the conf."""
    if resolution not in RESOLUTIONS:
        raise ZedConfError(f"Unknown resolution {resolution!r}; expected one of {list(RESOLUTIONS)}")
    if not conf.has_section("STEREO"):
        raise ZedConfError("Missing section [STEREO] in ZED conf")

    width, height = RESOLUTIONS[resolution]
    stereo = conf["STEREO"]

    baseline_mm = stereo.getfloat("Baseline", fallback=None)
    if baseline_mm is None:
        raise ZedConfError("Missing [STEREO] Baseline")

    rvec = np.array(
        [
            _stereo_value(stereo, "RX", resolution),
            _stereo_value(stereo, "CV", resolution),
            _stereo_value(stereo, "RZ", resolution),
        ]
    )
    rotation = rotation_vector_to_matrix(rvec)
    # Stereolabs convention: x2 = R x1 + T with T = [-Baseline, TY, TZ] (mm).
    translation = [
        -baseline_mm,
        _stereo_value(stereo, "TY", resolution),
        _stereo_value(stereo, "TZ", resolution),
    ]

    return {
        "left_camera_matrix": _camera_dict(conf, f"LEFT_CAM_{resolution}"),
        "right_camera_matrix": _camera_dict(conf, f"RIGHT_CAM_{resolution}"),
        "left_dist_coeffs": _dist_dict(conf, f"LEFT_CAM_{resolution}"),
        "right_dist_coeffs": _dist_dict(conf, f"RIGHT_CAM_{resolution}"),
        "rotation_matrix": {"rows": 3, "cols": 3, "data": rotation.tolist()},
        "translation_vector": {"rows": 3, "cols": 1, "data": translation},
        "baseline_mm": baseline_mm,
        "image_width_px": width,
        "image_height_px": height,
    }
