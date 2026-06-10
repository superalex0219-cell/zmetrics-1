"""Real step: per-particle metric sizes/volumes from SAM3 masks × stereo depth.

Replaces MockParticleVolumeStep when both real depth (ENABLE_REAL_STEREO) and
real segmentation (ENABLE_SAM3) are active.

Geometry notes:
- SAM3 polygons are normalized to the ORIGINAL left frame; the depth map lives
  in rectified space. Polygon vertices are mapped into rectified pixel
  coordinates with cv2.undistortPoints(R=R1, P=P1) using the same
  cv2.stereoRectify(alpha=0) call as CVRectificationStep, then rasterized.
- Depth units follow the calibration translation units; they are converted to
  mm via unit_to_mm = baseline_mm / ||T|| so the step works for calibrations
  stored in mm or m.
- Particle size = projected-area equivalent diameter (2D photoanalysis
  convention); volume = ellipsoid over the minAreaRect axes (a, b, b) — the
  unseen third axis is assumed equal to the minor axis.
"""

import io
import json
import time

import numpy as np

from app.pipeline.interfaces import PipelineContext, PipelineStep, StepResult

# Masks smaller than this (rectified pixels) carry no reliable metric signal.
MIN_MASK_PIXELS = 64
# Minimum fraction of mask pixels that must have valid (finite) depth.
MIN_DEPTH_COVERAGE = 0.3


class CVParticleVolumeStep(PipelineStep):
    step_name = "particle_volumes"

    async def execute(self, ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult:
        import cv2

        t0 = time.monotonic()
        base = f"sessions/{ctx.capture_session_id}/pipeline/particles"
        output_key = f"{base}/particle_list.json"

        # Idempotency
        try:
            ctx.storage_client.head_object(Bucket=ctx.bucket_artifacts, Key=output_key)
            return StepResult(
                step_name=self.step_name, success=True,
                output_artifact_keys=[output_key],
                duration_seconds=time.monotonic() - t0,
                metadata={"cached": True},
            )
        except Exception:
            pass

        try:
            session_base = f"sessions/{ctx.capture_session_id}/pipeline"

            def _get_json(key: str) -> dict:
                resp = ctx.storage_client.get_object(Bucket=ctx.bucket_artifacts, Key=key)
                return json.loads(resp["Body"].read())

            masks_data = _get_json(f"{session_base}/segmentation/masks.json")
            cal = _get_json(f"{session_base}/calibration_params.json")

            resp = ctx.storage_client.get_object(
                Bucket=ctx.bucket_artifacts,
                Key=f"{session_base}/depth_estimation/depth_map.npy",
            )
            depth_map = np.load(io.BytesIO(resp["Body"].read()))

            # Reproduce the rectification transform (same inputs as
            # CVRectificationStep → identical R1/P1).
            from app.pipeline.cv_rectification import (
                _dict_to_camera_matrix,
                _dict_to_dist,
                _dict_to_matrix,
            )

            K_l = _dict_to_camera_matrix(cal["left_camera_matrix"])
            D_l = _dict_to_dist(cal["left_dist_coeffs"])
            K_r = _dict_to_camera_matrix(cal["right_camera_matrix"])
            D_r = _dict_to_dist(cal["right_dist_coeffs"])
            R = _dict_to_matrix(cal["rotation_matrix"])
            T = _dict_to_matrix(cal["translation_vector"]).reshape(3, 1)
            w, h = cal["image_width_px"], cal["image_height_px"]

            R1, _, P1, _, _, _, _ = cv2.stereoRectify(K_l, D_l, K_r, D_r, (w, h), R, T, alpha=0)
            f_rect = float(P1[0, 0])  # rectified focal length, px

            # Depth units → mm (units follow the calibration translation vector)
            baseline_units = float(np.linalg.norm(T))
            if baseline_units <= 0:
                raise ValueError("Calibration translation vector has zero norm")
            unit_to_mm = float(cal["baseline_mm"]) / baseline_units

            if depth_map.shape != (h, w):
                raise ValueError(
                    f"Depth map shape {depth_map.shape} does not match calibration "
                    f"resolution ({h}, {w})"
                )

            mask_source = masks_data.get("source", "unknown")
            depth_backend = _depth_backend_from(previous_results)
            calibration_id = await _calibration_id(ctx)

            particles: list[dict] = []
            skipped = {"degenerate_polygon": 0, "too_small": 0, "low_depth_coverage": 0}

            for mask in masks_data.get("masks", []):
                poly_norm = mask.get("polygon_normalized") or []
                if len(poly_norm) < 3:
                    skipped["degenerate_polygon"] += 1
                    continue

                # Original-frame pixel coords → rectified pixel coords
                pts = np.array(poly_norm, dtype=np.float64) * np.array([w, h], dtype=np.float64)
                rect_pts = cv2.undistortPoints(
                    pts.reshape(-1, 1, 2), K_l, D_l, R=R1, P=P1
                ).reshape(-1, 2)

                raster = np.zeros((h, w), dtype=np.uint8)
                cv2.fillPoly(raster, [np.round(rect_pts).astype(np.int32)], 1)
                region = raster.astype(bool)
                n_px = int(region.sum())
                if n_px < MIN_MASK_PIXELS:
                    skipped["too_small"] += 1
                    continue

                depths = depth_map[region]
                valid = depths[np.isfinite(depths)]
                coverage = len(valid) / n_px
                if coverage < MIN_DEPTH_COVERAGE:
                    skipped["low_depth_coverage"] += 1
                    continue

                z_mm = float(np.median(valid)) * unit_to_mm
                mm_per_px = z_mm / f_rect

                area_mm2 = n_px * mm_per_px ** 2
                d_eq_mm = 2.0 * float(np.sqrt(area_mm2 / np.pi))

                # Ellipsoid volume over the fitted box axes (a, b, b)
                (_, _), (side_a, side_b), _ = cv2.minAreaRect(rect_pts.astype(np.float32))
                major_mm = max(side_a, side_b) * mm_per_px
                minor_mm = min(side_a, side_b) * mm_per_px
                volume_mm3 = (np.pi / 6.0) * major_mm * minor_mm * minor_mm
                volume_m3 = float(volume_mm3) * 1e-9

                particles.append({
                    "id": mask.get("id", len(particles)),
                    "equivalent_diameter_mm": d_eq_mm,
                    "volume_m3": volume_m3,
                    "major_axis_mm": float(major_mm),
                    "minor_axis_mm": float(minor_mm),
                    "median_depth_mm": z_mm,
                    "mask_pixels": n_px,
                    "depth_coverage": float(coverage),
                    "segmentation_confidence": float(mask.get("confidence", 0.0)),
                })

            total_volume_m3 = float(sum(p["volume_m3"] for p in particles))
            payload = {
                "source": "cv",
                "mask_source": mask_source,
                "depth_backend": depth_backend,
                "calibration_id": calibration_id,
                "n_particles": len(particles),
                "n_masks_input": len(masks_data.get("masks", [])),
                "n_skipped": skipped,
                "total_volume_m3": total_volume_m3,
                "mean_depth_coverage": (
                    float(np.mean([p["depth_coverage"] for p in particles])) if particles else 0.0
                ),
                "mean_segmentation_confidence": (
                    float(np.mean([p["segmentation_confidence"] for p in particles]))
                    if particles else 0.0
                ),
                "particles": particles,
            }

            ctx.storage_client.put_object(
                Bucket=ctx.bucket_artifacts,
                Key=output_key,
                Body=json.dumps(payload).encode(),
                ContentType="application/json",
            )

            return StepResult(
                step_name=self.step_name, success=True,
                output_artifact_keys=[output_key],
                duration_seconds=time.monotonic() - t0,
                metadata={
                    "source": "cv",
                    "mask_source": mask_source,
                    "n_particles": len(particles),
                    "n_skipped": skipped,
                    "total_volume_m3": total_volume_m3,
                },
            )

        except Exception as exc:
            return StepResult(
                step_name=self.step_name, success=False,
                output_artifact_keys=[],
                duration_seconds=time.monotonic() - t0,
                error=str(exc),
            )


def _depth_backend_from(previous_results: list[StepResult]) -> str:
    for r in previous_results:
        if r.step_name == "depth_estimation":
            backend = r.metadata.get("backend", "sgbm")
            ckpt = r.metadata.get("checkpoint")
            return f"{backend}/{ckpt}" if ckpt else backend
    return "unknown"


async def _calibration_id(ctx: PipelineContext) -> str | None:
    from sqlalchemy import select

    from app.db_models import CaptureSession

    row = (await ctx.db_session.execute(
        select(CaptureSession).where(CaptureSession.id == ctx.capture_session_id)
    )).scalar_one_or_none()
    if row is None or row.calibration_id is None:
        return None
    return str(row.calibration_id)
