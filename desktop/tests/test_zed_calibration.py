"""Tests for ZED factory conf parsing → CalibrationCreate payload."""
import math

import numpy as np
import pytest

from zmetrics_desktop.capture.zed_calibration import (
    ZedConfError,
    build_calibration_payload,
    parse_zed_conf,
    resolution_for_frame,
    rotation_vector_to_matrix,
)

SAMPLE_CONF = """\
[LEFT_CAM_2K]
fx=1068.5
fy=1068.13
cx=1106.14
cy=640.011
k1=-0.0592102
k2=0.0358082
p1=-0.000315399
p2=-8.94399e-05
k3=-0.0144553

[RIGHT_CAM_2K]
fx=1067.04
fy=1066.58
cx=1088.96
cy=647.771
k1=-0.0642587
k2=0.0436327
p1=-0.000369278
p2=-0.000588874
k3=-0.0180629

[LEFT_CAM_HD]
fx=534.25
fy=534.065
cx=639.57
cy=368.0055
k1=-0.0592102
k2=0.0358082
p1=-0.000315399
p2=-8.94399e-05
k3=-0.0144553

[RIGHT_CAM_HD]
fx=533.52
fy=533.29
cx=630.98
cy=371.8855
k1=-0.0642587
k2=0.0436327
p1=-0.000369278
p2=-0.000588874
k3=-0.0180629

[STEREO]
Baseline=120.14
TY=0.0942712
TZ=-0.234404
CV_2K=-0.00312288
CV_HD=-0.00312288
RX_2K=0.00364425
RX_HD=0.00364425
RZ_2K=-0.00102985
RZ_HD=-0.00102985
"""


@pytest.fixture
def conf():
    return parse_zed_conf(SAMPLE_CONF)


def test_resolution_for_frame_maps_split_sbs_sizes():
    assert resolution_for_frame(2208, 1242) == "2K"
    assert resolution_for_frame(1280, 720) == "HD"
    with pytest.raises(ZedConfError):
        resolution_for_frame(640, 480)


def test_payload_intrinsics_and_size(conf):
    payload = build_calibration_payload(conf, "2K")
    assert payload["left_camera_matrix"] == {
        "fx": 1068.5, "fy": 1068.13, "cx": 1106.14, "cy": 640.011,
    }
    assert payload["right_dist_coeffs"]["k3"] == -0.0180629
    assert payload["image_width_px"] == 2208
    assert payload["image_height_px"] == 1242
    assert payload["baseline_mm"] == 120.14


def test_payload_translation_negates_baseline(conf):
    payload = build_calibration_payload(conf, "2K")
    tx, ty, tz = payload["translation_vector"]["data"]
    assert tx == -120.14
    assert ty == pytest.approx(0.0942712)
    assert tz == pytest.approx(-0.234404)


def test_payload_rotation_is_orthonormal_and_small(conf):
    payload = build_calibration_payload(conf, "2K")
    R = np.array(payload["rotation_matrix"]["data"])
    assert R.shape == (3, 3)
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-12)
    assert np.allclose(R, np.eye(3), atol=0.01)  # factory angles are milliradians
    assert payload["rotation_matrix"]["rows"] == 3
    assert payload["rotation_matrix"]["cols"] == 3


def test_rodrigues_matches_known_rotation():
    # 90° around Z: x → y
    R = rotation_vector_to_matrix(np.array([0.0, 0.0, math.pi / 2]))
    assert np.allclose(R @ np.array([1.0, 0.0, 0.0]), [0.0, 1.0, 0.0], atol=1e-12)
    # zero vector → identity
    assert np.allclose(rotation_vector_to_matrix(np.zeros(3)), np.eye(3))


def test_per_resolution_sections_select_scaled_intrinsics(conf):
    hd = build_calibration_payload(conf, "HD")
    assert hd["left_camera_matrix"]["fx"] == 534.25
    assert hd["image_width_px"] == 1280


def test_missing_section_raises(conf):
    with pytest.raises(ZedConfError):
        build_calibration_payload(conf, "VGA")  # sections absent in sample
    with pytest.raises(ZedConfError):
        build_calibration_payload(conf, "4K")  # unknown resolution name


def test_suffixed_ty_tz_fallback():
    text = SAMPLE_CONF.replace("TY=0.0942712", "TY_2K=0.0942712").replace(
        "TZ=-0.234404", "TZ_2K=-0.234404"
    )
    payload = build_calibration_payload(parse_zed_conf(text), "2K")
    assert payload["translation_vector"]["data"][1] == pytest.approx(0.0942712)
