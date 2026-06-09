import numpy as np

from zmetrics_desktop.capture.stereo import split_side_by_side


def _frame(height: int, width: int) -> np.ndarray:
    # Distinct left/right halves so we can assert the split picked the right columns.
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, : width // 2] = 10
    frame[:, width // 2 :] = 200
    return frame


def test_wide_frame_is_split_into_left_right():
    frame = _frame(100, 300)  # aspect 3.0 > 1.8
    result = split_side_by_side(frame)

    assert result.side_by_side is True
    assert result.right is not None
    assert result.width == 150
    assert result.height == 100
    assert result.left.shape == (100, 150, 3)
    assert result.right.shape == (100, 150, 3)
    assert int(result.left.mean()) == 10
    assert int(result.right.mean()) == 200


def test_odd_width_drops_last_column():
    frame = _frame(10, 301)  # aspect ~30 > 1.8, odd width
    result = split_side_by_side(frame)

    assert result.side_by_side is True
    assert result.width == 150  # 301 // 2
    assert result.left.shape[1] == 150
    assert result.right.shape[1] == 150


def test_square_frame_is_not_side_by_side():
    frame = _frame(100, 100)  # aspect 1.0 < 1.8
    result = split_side_by_side(frame)

    assert result.side_by_side is False
    assert result.right is None
    assert result.width == 100
    assert result.height == 100


def test_zero_dimension_rejected():
    import pytest

    with pytest.raises(ValueError):
        split_side_by_side(np.zeros((0, 10, 3), dtype=np.uint8))
