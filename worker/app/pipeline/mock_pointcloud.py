"""Mock step: 3D point cloud generation."""

import asyncio
import io
import json
import time

from app.pipeline.interfaces import PipelineContext, PipelineStep, StepResult, pipeline_prefix


class MockPointCloudStep(PipelineStep):
    step_name = "point_cloud"

    async def execute(self, ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult:
        t0 = time.monotonic()
        await asyncio.sleep(0.25)

        import numpy as np

        rng = np.random.default_rng(seed=42)
        n_points = 5000
        # Synthetic point cloud: random points in a 10m x 10m x 3m volume (x, y, z in meters)
        points = rng.uniform([0, 0, 0], [10, 10, 3], size=(n_points, 3)).astype(np.float32)

        # Write as minimal PLY ASCII
        ply_header = (
            "ply\n"
            "format ascii 1.0\n"
            f"element vertex {n_points}\n"
            "property float x\n"
            "property float y\n"
            "property float z\n"
            "end_header\n"
        )
        ply_data = ply_header + "\n".join(f"{x:.4f} {y:.4f} {z:.4f}" for x, y, z in points)

        output_key = f"{pipeline_prefix(ctx)}/pointcloud/point_cloud.ply"
        ctx.storage_client.put_object(
            Bucket=ctx.bucket_artifacts,
            Key=output_key,
            Body=ply_data.encode(),
            ContentType="application/octet-stream",
        )

        meta_key = f"{pipeline_prefix(ctx)}/pointcloud/meta.json"
        ctx.storage_client.put_object(
            Bucket=ctx.bucket_artifacts,
            Key=meta_key,
            Body=json.dumps({"n_points": n_points, "bounds_m": {"x": [0, 10], "y": [0, 10], "z": [0, 3]}}).encode(),
            ContentType="application/json",
        )

        return StepResult(
            step_name=self.step_name,
            success=True,
            output_artifact_keys=[output_key, meta_key],
            duration_seconds=time.monotonic() - t0,
            metadata={"n_points": n_points},
        )
