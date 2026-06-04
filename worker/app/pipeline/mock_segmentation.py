"""Mock step: instance segmentation (rock particle masks)."""

import asyncio
import json
import time

from app.pipeline.interfaces import PipelineContext, PipelineStep, StepResult


class MockSegmentationStep(PipelineStep):
    step_name = "segmentation"

    async def execute(self, ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult:
        t0 = time.monotonic()
        await asyncio.sleep(0.3)

        import numpy as np

        rng = np.random.default_rng(seed=123)
        n_particles = rng.integers(80, 200)

        # Synthetic masks: ellipse bounding boxes in image coordinates (normalized 0..1)
        masks = []
        for i in range(int(n_particles)):
            cx = float(rng.uniform(0.05, 0.95))
            cy = float(rng.uniform(0.05, 0.95))
            rx = float(rng.uniform(0.01, 0.08))
            ry = float(rng.uniform(0.01, 0.06))
            # Approximate ellipse polygon (8 points)
            angles = [k * 3.14159 / 4 for k in range(8)]
            polygon = [[cx + rx * float(np.cos(a)), cy + ry * float(np.sin(a))] for a in angles]
            masks.append({
                "id": i,
                "bbox_normalized": [cx - rx, cy - ry, cx + rx, cy + ry],
                "polygon_normalized": polygon,
                "confidence": float(rng.uniform(0.7, 0.99)),
            })

        output_key = f"sessions/{ctx.capture_session_id}/pipeline/segmentation/masks.json"
        ctx.storage_client.put_object(
            Bucket=ctx.bucket_artifacts,
            Key=output_key,
            Body=json.dumps({"n_masks": len(masks), "masks": masks}).encode(),
            ContentType="application/json",
        )

        return StepResult(
            step_name=self.step_name,
            success=True,
            output_artifact_keys=[output_key],
            duration_seconds=time.monotonic() - t0,
            metadata={"n_particles_detected": len(masks)},
        )
