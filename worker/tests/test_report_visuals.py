"""Tests: ReportVisualsStep — mask overlay + colorized depth (REPORT-X)."""

from __future__ import annotations

import io
import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from app.pipeline.cv_report_visuals import (
    ReportVisualsStep,
    render_depth_color,
    render_mask_overlay,
)
from app.pipeline.interfaces import PipelineContext


def make_s3():
    storage: dict[str, bytes] = {}
    mock = MagicMock()

    def put_object(Bucket, Key, Body, **kwargs):
        storage[f"{Bucket}/{Key}"] = Body if isinstance(Body, bytes) else Body.read()

    def get_object(Bucket, Key):
        if f"{Bucket}/{Key}" not in storage:
            raise KeyError(Key)
        data = storage[f"{Bucket}/{Key}"]
        return {"Body": MagicMock(read=lambda: data)}

    mock.put_object.side_effect = put_object
    mock.get_object.side_effect = get_object
    mock.head_object.side_effect = Exception("404")
    mock._storage = storage
    return mock


def make_ctx(s3, db=None) -> PipelineContext:
    if db is None:
        db = MagicMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None  # нет артефакта кадра
        db.execute = AsyncMock(return_value=result)
    return PipelineContext(
        job_id=uuid.uuid4(),
        capture_session_id=uuid.uuid4(),
        storage_client=s3,
        db_session=db,
    )


def test_render_depth_color_shapes_and_invalid_pixels():
    depth = np.full((40, 60), 2000.0, dtype=np.float32)
    depth[:10, :10] = np.nan
    img = render_depth_color(depth)
    assert img.shape == (40, 60, 3)
    assert (img[0, 0] == [0, 0, 0]).all()  # NaN → чёрный
    assert img[20, 20].any()  # валидная глубина окрашена

    assert render_depth_color(np.full((4, 4), np.nan, dtype=np.float32)) is None


def test_render_mask_overlay_draws_polygons():
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    masks = [{
        "polygon_normalized": [[0.1, 0.1], [0.5, 0.1], [0.5, 0.5], [0.1, 0.5]],
        "confidence": 0.9,
    }]
    overlay = render_mask_overlay(frame, masks)
    assert overlay.shape == frame.shape
    assert overlay[30, 60].any()  # внутри полигона появился цвет
    assert not overlay[90, 190].any()  # вне полигона осталось чёрным


async def test_step_degrades_gracefully_without_inputs():
    """Нет глубины, кадра и масок — шаг всё равно success (вспомогательный)."""
    s3 = make_s3()
    ctx = make_ctx(s3)

    result = await ReportVisualsStep().execute(ctx, [])

    assert result.success
    assert result.output_artifact_keys == []
    assert "skipped" in result.metadata["depth_color"]
    assert "skipped" in result.metadata["mask_overlay"]


async def test_step_writes_depth_png_when_depth_exists():
    s3 = make_s3()
    ctx = make_ctx(s3)
    depth = np.full((30, 40), 1500.0, dtype=np.float32)
    buf = io.BytesIO()
    np.save(buf, depth)
    s3.put_object(
        Bucket=ctx.bucket_artifacts,
        Key=f"sessions/{ctx.capture_session_id}/pipeline/depth_estimation/depth_map.npy",
        Body=buf.getvalue(),
    )

    result = await ReportVisualsStep().execute(ctx, [])

    assert result.success
    depth_key = f"sessions/{ctx.capture_session_id}/pipeline/report_visuals/depth_color.png"
    assert depth_key in result.output_artifact_keys
    png = s3._storage[f"{ctx.bucket_artifacts}/{depth_key}"]
    assert png.startswith(b"\x89PNG")
