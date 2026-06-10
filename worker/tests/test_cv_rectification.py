"""Tests: calibration matrix parsing + stub-calibration rejection."""

from __future__ import annotations

import numpy as np

from app.pipeline.cv_rectification import _dict_to_matrix


def test_dict_to_matrix_nested_3x3():
    m = _dict_to_matrix({"data": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]})
    assert m.shape == (3, 3)


def test_dict_to_matrix_flat_9_reshapes():
    # The desktop test-device stub stores rotation as a flat 9-element list —
    # this used to reach cv2.stereoRectify/Rodrigues as [1 x 9] and crash.
    m = _dict_to_matrix({"rows": 3, "cols": 3, "data": [1.0, 0, 0, 0, 1.0, 0, 0, 0, 1.0]})
    assert m.shape == (3, 3)
    assert np.allclose(m, np.eye(3))


def test_dict_to_matrix_flat_translation():
    t = _dict_to_matrix({"rows": 3, "cols": 1, "data": [-120.0, 0.0, 0.0]})
    assert t.shape == (3, 1)
    t2 = _dict_to_matrix({"data": [-120.0, 0.0, 0.0]})  # no rows/cols → inferred
    assert t2.shape == (3, 1)
