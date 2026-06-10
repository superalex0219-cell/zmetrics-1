"""Real step: granulometric distribution from CV-measured particles.

Replaces MockGranulometryStep when the real particle step ran. Differences
from the mock:
- cumulative passing is VOLUME-weighted (the mock used particle counts),
  matching how sieve analysis reports % passing by mass;
- confidence_score is computed from segmentation confidence, depth coverage
  and sample size — not hardcoded;
- confidence_notes carry the real-CV provenance required by safety rules:
  segmentation model, depth backend, calibration ID.

Final step: writes result.json to MinIO and creates the AnalysisResult row.
"""

import json
import time

import numpy as np

from app.pipeline.interfaces import PipelineContext, PipelineStep, StepResult
from app.pipeline.mock_granulometry import _fit_rosin_rammler, _save_analysis_result

OVERSIZE_THRESHOLD_MM = 500.0
FINES_THRESHOLD_MM = 25.0

# Below this sample size the distribution statistics are considered unstable
# and the confidence score is scaled down proportionally.
FULL_CONFIDENCE_PARTICLE_COUNT = 30


class CVGranulometryStep(PipelineStep):
    step_name = "granulometry"

    async def execute(self, ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult:
        t0 = time.monotonic()
        output_key = f"sessions/{ctx.capture_session_id}/pipeline/granulometry/result.json"

        try:
            particle_key = f"sessions/{ctx.capture_session_id}/pipeline/particles/particle_list.json"
            resp = ctx.storage_client.get_object(Bucket=ctx.bucket_artifacts, Key=particle_key)
            particle_data = json.loads(resp["Body"].read())

            particles = particle_data.get("particles", [])
            confidence_score, confidence_notes = _confidence(particle_data)

            if particles:
                diameters = np.array([p["equivalent_diameter_mm"] for p in particles], dtype=np.float64)
                volumes = np.array([p["volume_m3"] for p in particles], dtype=np.float64)

                order = np.argsort(diameters)
                d_sorted = diameters[order]
                v_sorted = volumes[order]
                total_volume = float(v_sorted.sum())

                # Volume-weighted cumulative passing curve (% of total volume
                # contained in particles of this size or smaller).
                cum_passing_pct = np.cumsum(v_sorted) / total_volume * 100.0

                p10 = float(np.interp(10.0, cum_passing_pct, d_sorted))
                p50 = float(np.interp(50.0, cum_passing_pct, d_sorted))
                p80 = float(np.interp(80.0, cum_passing_pct, d_sorted))

                rr_n, rr_xc = _fit_rosin_rammler(d_sorted, cum_passing_pct)
                if rr_n is None:
                    confidence_notes += " | Rosin-Rammler fit failed"

                table_pcts = np.linspace(0, 100, 20)
                dist_table = [
                    {
                        "size_mm": float(round(np.interp(cp, cum_passing_pct, d_sorted), 1)),
                        "cumulative_passing_pct": float(round(cp, 2)),
                    }
                    for cp in table_pcts
                ]

                oversize_pct = float(
                    100.0 - np.interp(OVERSIZE_THRESHOLD_MM, d_sorted, cum_passing_pct,
                                      left=0.0, right=100.0)
                )
                fines_pct = float(
                    np.interp(FINES_THRESHOLD_MM, d_sorted, cum_passing_pct,
                              left=0.0, right=100.0)
                )

                result_payload = {
                    "analysis_method": "cv",
                    "p10_mm": round(p10, 3),
                    "p50_mm": round(p50, 3),
                    "p80_mm": round(p80, 3),
                    "rosin_rammler_n": round(rr_n, 6) if rr_n is not None else None,
                    "rosin_rammler_xc": round(rr_xc, 3) if rr_xc is not None else None,
                    "uniformity_index": round(rr_n, 6) if rr_n is not None else None,
                    "oversize_percent": round(oversize_pct, 3),
                    "fines_percent": round(fines_pct, 3),
                    "total_particles_counted": len(particles),
                    "total_volume_m3": round(total_volume, 4),
                    "confidence_score": round(confidence_score, 4),
                    "confidence_notes": confidence_notes,
                    "size_distribution": dist_table,
                }
            else:
                # No particles detected — record an honest empty result instead
                # of inventing a distribution.
                result_payload = {
                    "analysis_method": "cv",
                    "p10_mm": None,
                    "p50_mm": None,
                    "p80_mm": None,
                    "rosin_rammler_n": None,
                    "rosin_rammler_xc": None,
                    "uniformity_index": None,
                    "oversize_percent": None,
                    "fines_percent": None,
                    "total_particles_counted": 0,
                    "total_volume_m3": 0.0,
                    "confidence_score": 0.0,
                    "confidence_notes": "⚠ No particles measured — " + confidence_notes,
                    "size_distribution": [],
                }

            ctx.storage_client.put_object(
                Bucket=ctx.bucket_artifacts,
                Key=output_key,
                Body=json.dumps(result_payload).encode(),
                ContentType="application/json",
            )

            await _save_analysis_result(ctx, result_payload)

            return StepResult(
                step_name=self.step_name, success=True,
                output_artifact_keys=[output_key],
                duration_seconds=time.monotonic() - t0,
                metadata={
                    "analysis_method": "cv",
                    "p10_mm": result_payload["p10_mm"],
                    "p50_mm": result_payload["p50_mm"],
                    "p80_mm": result_payload["p80_mm"],
                    "n_particles": result_payload["total_particles_counted"],
                    "confidence_score": result_payload["confidence_score"],
                    "rosin_rammler_fit_failed": result_payload["rosin_rammler_n"] is None,
                },
            )

        except Exception as exc:
            return StepResult(
                step_name=self.step_name, success=False,
                output_artifact_keys=[],
                duration_seconds=time.monotonic() - t0,
                error=str(exc),
            )


def _confidence(particle_data: dict) -> tuple[float, str]:
    """Compute confidence score + provenance notes from the particle payload."""
    n = int(particle_data.get("n_particles", 0))
    mask_source = particle_data.get("mask_source", "unknown")
    depth_backend = particle_data.get("depth_backend", "unknown")
    calibration_id = particle_data.get("calibration_id") or "unknown"
    mean_conf = float(particle_data.get("mean_segmentation_confidence", 0.0))
    mean_cov = float(particle_data.get("mean_depth_coverage", 0.0))
    skipped = particle_data.get("n_skipped", {})
    n_skipped = sum(skipped.values()) if isinstance(skipped, dict) else 0

    count_factor = min(1.0, n / FULL_CONFIDENCE_PARTICLE_COUNT)
    score = max(0.0, min(1.0, mean_conf * mean_cov * count_factor))

    notes = (
        f"Real CV pipeline: segmentation={mask_source}, depth={depth_backend}, "
        f"calibration_id={calibration_id}; {n} particles measured, {n_skipped} masks skipped"
    )

    if mask_source != "sam3":
        # Synthetic fallback masks → the geometry is fictional even though the
        # depth is real. Label loudly and cap confidence.
        score = min(score, 0.2)
        notes = "⚠ Synthetic fallback masks — sizes are NOT from real segmentation | " + notes

    if score < 0.5:
        notes += " | ⚠ Low confidence — results require careful human review"

    return score, notes
