"""Mock step: particle volume estimation."""

import asyncio
import json
import time

from app.pipeline.interfaces import PipelineContext, PipelineStep, StepResult, pipeline_prefix


class MockParticleVolumeStep(PipelineStep):
    step_name = "particle_volumes"

    async def execute(self, ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult:
        t0 = time.monotonic()
        await asyncio.sleep(0.2)

        import numpy as np

        rng = np.random.default_rng(seed=int(str(ctx.job_id).replace("-", "")[:8], 16))

        # Synthetic particle size distribution: log-normal (typical quarry blast fragmentation)
        # Mean ~250mm, geometric std ~1.8
        n_particles = 150
        log_mean = np.log(0.250)  # 250mm in meters
        log_std = np.log(1.8)
        diameters_m = rng.lognormal(mean=log_mean, sigma=log_std, size=n_particles)
        # Clamp to realistic range 5mm–2000mm
        diameters_m = np.clip(diameters_m, 0.005, 2.0)
        # Approximate volume as sphere: V = (4/3)*pi*(d/2)^3
        volumes_m3 = (4.0 / 3.0) * np.pi * (diameters_m / 2.0) ** 3

        particles = [
            {
                "id": i,
                "equivalent_diameter_mm": float(round(d * 1000, 1)),
                "volume_m3": float(v),
            }
            for i, (d, v) in enumerate(zip(diameters_m, volumes_m3))
        ]

        output_key = f"{pipeline_prefix(ctx)}/particles/particle_list.json"
        ctx.storage_client.put_object(
            Bucket=ctx.bucket_artifacts,
            Key=output_key,
            Body=json.dumps({
                "n_particles": len(particles),
                "total_volume_m3": float(volumes_m3.sum()),
                "particles": particles,
            }).encode(),
            ContentType="application/json",
        )

        return StepResult(
            step_name=self.step_name,
            success=True,
            output_artifact_keys=[output_key],
            duration_seconds=time.monotonic() - t0,
            metadata={
                "n_particles": len(particles),
                "total_volume_m3": float(volumes_m3.sum()),
            },
        )
