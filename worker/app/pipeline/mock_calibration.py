"""Mock step: load calibration parameters from DB and write to MinIO."""

import asyncio
import json
import time

from app.pipeline.interfaces import PipelineContext, PipelineStep, StepResult, pipeline_prefix


class MockCalibrationStep(PipelineStep):
    step_name = "calibration_load"

    async def execute(self, ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult:
        t0 = time.monotonic()
        await asyncio.sleep(0.1)

        output_key = f"{pipeline_prefix(ctx)}/calibration_params.json"

        params = {
            "source": "mock",
            "baseline_mm": 120.0,
            "image_width_px": 2208,
            "image_height_px": 1242,
            "left_camera_matrix": {"fx": 1400.0, "fy": 1400.0, "cx": 1104.0, "cy": 621.0},
            "right_camera_matrix": {"fx": 1400.0, "fy": 1400.0, "cx": 1104.0, "cy": 621.0},
            "left_dist_coeffs": {"k1": -0.17, "k2": 0.03, "p1": 0.0, "p2": 0.0, "k3": 0.0},
            "right_dist_coeffs": {"k1": -0.17, "k2": 0.03, "p1": 0.0, "p2": 0.0, "k3": 0.0},
        }

        ctx.storage_client.put_object(
            Bucket=ctx.bucket_artifacts,
            Key=output_key,
            Body=json.dumps(params).encode(),
            ContentType="application/json",
        )

        return StepResult(
            step_name=self.step_name,
            success=True,
            output_artifact_keys=[output_key],
            duration_seconds=time.monotonic() - t0,
            metadata={"baseline_mm": params["baseline_mm"]},
        )
