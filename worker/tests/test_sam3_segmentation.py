"""SAM3 segmentation unit checks that avoid loading the heavy model."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.pipeline.sam3_segmentation import (
    _SAM3_REQUIRED_TORCH_ATTR,
    _validate_sam3_runtime,
)


def test_sam3_runtime_validation_accepts_required_torch_dtype():
    torch_stub = SimpleNamespace(__version__="2.11.0")
    setattr(torch_stub, _SAM3_REQUIRED_TORCH_ATTR, object())

    _validate_sam3_runtime(torch_stub)


def test_sam3_runtime_validation_rejects_old_torch():
    torch_stub = SimpleNamespace(__version__="2.5.1+cu121")

    with pytest.raises(RuntimeError, match="SAM3 requires a newer PyTorch"):
        _validate_sam3_runtime(torch_stub)
