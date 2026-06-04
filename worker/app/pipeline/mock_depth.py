"""Mock step: disparity/depth estimation."""

import asyncio
import io
import json
import time

from app.pipeline.interfaces import PipelineContext, PipelineStep, StepResult


class MockDepthStep(PipelineStep):
    step_name = "depth_estimation"

    async def execute(self, ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult:
        t0 = time.monotonic()
        await asyncio.sleep(0.2)

        import numpy as np

        # Synthetic depth map: random depths between 2m and 8m (meters), shaped for image size
        rng = np.random.default_rng(seed=int(str(ctx.capture_session_id).replace("-", "")[:8], 16))
        depth_map = rng.uniform(2.0, 8.0, size=(128, 228)).astype(np.float32)

        output_key = f"sessions/{ctx.capture_session_id}/pipeline/depth/depth_map.npy"
        buf = io.BytesIO()
        np.save(buf, depth_map)
        buf.seek(0)

        ctx.storage_client.put_object(
            Bucket=ctx.bucket_artifacts,
            Key=output_key,
            Body=buf.getvalue(),
            ContentType="application/octet-stream",
        )

        stats_key = f"sessions/{ctx.capture_session_id}/pipeline/depth/depth_stats.json"
        ctx.storage_client.put_object(
            Bucket=ctx.bucket_artifacts,
            Key=stats_key,
            Body=json.dumps({
                "min_m": float(depth_map.min()),
                "max_m": float(depth_map.max()),
                "mean_m": float(depth_map.mean()),
                "shape": list(depth_map.shape),
            }).encode(),
            ContentType="application/json",
        )

        return StepResult(
            step_name=self.step_name,
            success=True,
            output_artifact_keys=[output_key, stats_key],
            duration_seconds=time.monotonic() - t0,
            metadata={"depth_min_m": float(depth_map.min()), "depth_max_m": float(depth_map.max())},
        )
