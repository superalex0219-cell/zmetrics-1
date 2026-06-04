"""Tests: pipeline step interface and mock step behavior."""

from __future__ import annotations

import asyncio
import json
import uuid
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.interfaces import Pipeline, PipelineContext, PipelineStep, PipelineStepError, StepResult


def make_mock_s3():
    """Create a simple in-memory mock S3 client."""
    storage: dict[str, bytes] = {}

    mock = MagicMock()

    def put_object(Bucket, Key, Body, **kwargs):
        storage[f"{Bucket}/{Key}"] = Body if isinstance(Body, bytes) else Body.read()

    def get_object(Bucket, Key):
        data = storage.get(f"{Bucket}/{Key}", b"{}")
        return {"Body": MagicMock(read=lambda: data)}

    mock.put_object.side_effect = put_object
    mock.get_object.side_effect = get_object
    mock._storage = storage
    return mock


def make_ctx(s3_mock=None) -> PipelineContext:
    return PipelineContext(
        job_id=uuid.uuid4(),
        capture_session_id=uuid.uuid4(),
        storage_client=s3_mock or make_mock_s3(),
        db_session=MagicMock(),
    )


# --- Interface tests ---

class _OkStep(PipelineStep):
    step_name = "ok_step"

    async def execute(self, ctx, prev):
        return StepResult(step_name=self.step_name, success=True, output_artifact_keys=[], duration_seconds=0.0)


class _FailStep(PipelineStep):
    step_name = "fail_step"

    async def execute(self, ctx, prev):
        return StepResult(step_name=self.step_name, success=False, output_artifact_keys=[], duration_seconds=0.0, error="intentional failure")


@pytest.mark.asyncio
async def test_pipeline_runs_ok_steps():
    ctx = make_ctx()
    results = await Pipeline([_OkStep(), _OkStep()]).run(ctx)
    assert len(results) == 2
    assert all(r.success for r in results)


@pytest.mark.asyncio
async def test_pipeline_raises_on_failed_step():
    ctx = make_ctx()
    with pytest.raises(PipelineStepError) as exc_info:
        await Pipeline([_OkStep(), _FailStep(), _OkStep()]).run(ctx)
    assert exc_info.value.step_name == "fail_step"


# --- Mock step smoke tests ---

@pytest.mark.asyncio
async def test_mock_calibration_step():
    from app.pipeline.mock_calibration import MockCalibrationStep
    s3 = make_mock_s3()
    ctx = make_ctx(s3)
    result = await MockCalibrationStep().execute(ctx, [])
    assert result.success
    assert len(result.output_artifact_keys) == 1
    # Verify artifact was written to mock S3
    key = result.output_artifact_keys[0]
    assert f"{ctx.bucket_artifacts}/{key}" in s3._storage


@pytest.mark.asyncio
async def test_mock_segmentation_produces_masks():
    from app.pipeline.mock_segmentation import MockSegmentationStep
    s3 = make_mock_s3()
    ctx = make_ctx(s3)
    result = await MockSegmentationStep().execute(ctx, [])
    assert result.success
    assert result.metadata.get("n_particles_detected", 0) > 0


@pytest.mark.asyncio
async def test_mock_particles_produces_distribution():
    from app.pipeline.mock_particles import MockParticleVolumeStep
    s3 = make_mock_s3()
    ctx = make_ctx(s3)
    result = await MockParticleVolumeStep().execute(ctx, [])
    assert result.success
    assert result.metadata["n_particles"] > 0
    assert result.metadata["total_volume_m3"] > 0


@pytest.mark.asyncio
async def test_full_mock_pipeline_integration():
    """Run all mock steps end-to-end (excluding DB write in granulometry)."""
    from app.pipeline.mock_calibration import MockCalibrationStep
    from app.pipeline.mock_depth import MockDepthStep
    from app.pipeline.mock_particles import MockParticleVolumeStep
    from app.pipeline.mock_pointcloud import MockPointCloudStep
    from app.pipeline.mock_rectification import MockRectificationStep
    from app.pipeline.mock_segmentation import MockSegmentationStep

    s3 = make_mock_s3()
    ctx = make_ctx(s3)

    steps = [
        MockCalibrationStep(),
        MockRectificationStep(),
        MockDepthStep(),
        MockPointCloudStep(),
        MockSegmentationStep(),
        MockParticleVolumeStep(),
    ]

    results = await Pipeline(steps).run(ctx)
    assert len(results) == 6
    assert all(r.success for r in results)
    total_artifacts = sum(len(r.output_artifact_keys) for r in results)
    assert total_artifacts >= 6
