"""
Mock step: granulometric distribution calculation.

Computes P10/P50/P80, fits Rosin-Rammler parameters, and creates the AnalysisResult DB record.
This is the final step; it writes to both MinIO and the database.
"""

import asyncio
import json
import time

from app.pipeline.interfaces import PipelineContext, PipelineStep, StepResult


class MockGranulometryStep(PipelineStep):
    step_name = "granulometry"

    async def execute(self, ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult:
        t0 = time.monotonic()
        await asyncio.sleep(0.1)

        import numpy as np
        from scipy.optimize import curve_fit

        # Load particle list from previous step
        particle_key = f"sessions/{ctx.capture_session_id}/pipeline/particles/particle_list.json"
        try:
            resp = ctx.storage_client.get_object(Bucket=ctx.bucket_artifacts, Key=particle_key)
            particle_data = json.loads(resp["Body"].read())
        except Exception:
            # Fallback: generate synthetic data if particle step artifact missing
            rng = np.random.default_rng(seed=0)
            diameters_mm = rng.lognormal(mean=np.log(250), sigma=np.log(1.8), size=150)
            diameters_mm = np.clip(diameters_mm, 5, 2000)
            volumes_m3 = (4.0 / 3.0) * np.pi * (diameters_mm / 2000.0) ** 3
            particle_data = {
                "particles": [
                    {"equivalent_diameter_mm": float(d), "volume_m3": float(v)}
                    for d, v in zip(diameters_mm, volumes_m3)
                ],
                "total_volume_m3": float(volumes_m3.sum()),
            }

        particles = particle_data["particles"]
        diameters = np.array([p["equivalent_diameter_mm"] for p in particles])
        total_volume = float(particle_data.get("total_volume_m3", 0.0))

        diameters_sorted = np.sort(diameters)
        n = len(diameters_sorted)
        cumulative_pct = np.arange(1, n + 1) / n * 100.0

        # P-values (size at which X% of material passes)
        p10 = float(np.interp(10.0, cumulative_pct, diameters_sorted))
        p50 = float(np.interp(50.0, cumulative_pct, diameters_sorted))
        p80 = float(np.interp(80.0, cumulative_pct, diameters_sorted))

        # Rosin-Rammler fit: R(x) = exp(-(x/xc)^n)
        # Linearize: ln(-ln(R)) = n * ln(x) - n * ln(xc)
        rr_n, rr_xc = _fit_rosin_rammler(diameters_sorted, cumulative_pct)

        # Build size distribution table (20 points)
        size_steps = np.percentile(diameters_sorted, np.linspace(0, 100, 20))
        dist_table = [
            {"size_mm": float(round(s, 1)), "cumulative_passing_pct": float(round(cp, 2))}
            for s, cp in zip(size_steps, np.linspace(0, 100, 20))
        ]

        # Oversize/fines thresholds (typical quarry: oversize >500mm, fines <25mm)
        oversize_threshold_mm = 500.0
        fines_threshold_mm = 25.0
        oversize_pct = float(100.0 - np.interp(oversize_threshold_mm, diameters_sorted, cumulative_pct))
        fines_pct = float(np.interp(fines_threshold_mm, diameters_sorted, cumulative_pct))

        result_payload = {
            "p10_mm": round(p10, 3),
            "p50_mm": round(p50, 3),
            "p80_mm": round(p80, 3),
            "rosin_rammler_n": round(rr_n, 6) if rr_n else None,
            "rosin_rammler_xc": round(rr_xc, 3) if rr_xc else None,
            "uniformity_index": round(rr_n, 6) if rr_n else None,
            "oversize_percent": round(oversize_pct, 3),
            "fines_percent": round(fines_pct, 3),
            "total_particles_counted": len(particles),
            "total_volume_m3": round(total_volume, 4),
            "confidence_score": 0.72,
            "confidence_notes": "mock pipeline — values are synthetic, not from real CV",
            "size_distribution": dist_table,
        }

        # Write to MinIO
        output_key = f"sessions/{ctx.capture_session_id}/pipeline/granulometry/result.json"
        ctx.storage_client.put_object(
            Bucket=ctx.bucket_artifacts,
            Key=output_key,
            Body=json.dumps(result_payload).encode(),
            ContentType="application/json",
        )

        # Write AnalysisResult to DB
        await _save_analysis_result(ctx, result_payload)

        return StepResult(
            step_name=self.step_name,
            success=True,
            output_artifact_keys=[output_key],
            duration_seconds=time.monotonic() - t0,
            metadata={
                "p10_mm": result_payload["p10_mm"],
                "p50_mm": result_payload["p50_mm"],
                "p80_mm": result_payload["p80_mm"],
                "confidence_score": result_payload["confidence_score"],
            },
        )


def _fit_rosin_rammler(
    diameters_sorted: "np.ndarray",
    cumulative_pct: "np.ndarray",
) -> tuple[float | None, float | None]:
    try:
        import numpy as np
        passing_frac = cumulative_pct / 100.0
        # Exclude 0% and 100% (log of 0 is undefined)
        mask = (passing_frac > 0.01) & (passing_frac < 0.99)
        x = diameters_sorted[mask]
        y = passing_frac[mask]
        ln_x = np.log(x)
        ln_neg_ln_r = np.log(-np.log(1.0 - y))

        # Linear regression: ln(-ln(1-F)) = n * ln(x) - n * ln(xc)
        coeffs = np.polyfit(ln_x, ln_neg_ln_r, 1)
        n = float(coeffs[0])
        xc = float(np.exp(-coeffs[1] / n)) if n != 0 else None
        return n, xc
    except Exception:
        return None, None


async def _save_analysis_result(ctx: PipelineContext, payload: dict) -> None:
    from sqlalchemy import select, update
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db_models import AnalysisResult

    db: AsyncSession = ctx.db_session

    result_obj = AnalysisResult(
        job_id=ctx.job_id,
        p10_mm=payload["p10_mm"],
        p50_mm=payload["p50_mm"],
        p80_mm=payload["p80_mm"],
        rosin_rammler_n=payload["rosin_rammler_n"],
        rosin_rammler_xc=payload["rosin_rammler_xc"],
        uniformity_index=payload["uniformity_index"],
        oversize_percent=payload["oversize_percent"],
        fines_percent=payload["fines_percent"],
        total_particles_counted=payload["total_particles_counted"],
        total_volume_m3=payload["total_volume_m3"],
        confidence_score=payload["confidence_score"],
        confidence_notes=payload["confidence_notes"],
        size_distribution=payload["size_distribution"],
    )
    db.add(result_obj)
    await db.flush()
