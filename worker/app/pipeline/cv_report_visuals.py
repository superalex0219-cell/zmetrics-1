"""Report visuals: mask overlay PNG + colorized depth PNG for REPORT-X exports.

Auxiliary step — it must NEVER fail the job: a missing frame or depth map only
reduces what the exported report can show, so every branch degrades gracefully
and the StepResult is always success=True (problems are recorded in metadata).

Outputs under ``{pipeline_prefix}/report_visuals/``:
- ``mask_overlay.png``  — the ORIGINAL left frame with segmentation polygons
  (masks.json polygons are normalized to the original frame, so no remapping)
- ``depth_color.png``   — depth_map.npy normalized to its 2–98 percentile range
  and colorized (JET); invalid pixels are black
"""

import io
import json
import time

import numpy as np

from app.pipeline.interfaces import PipelineContext, PipelineStep, StepResult, pipeline_prefix

# Cap overlay size — report pages don't need the full 2.2K frame.
MAX_VISUAL_WIDTH = 1280


async def _fetch_left_frame_bgr(ctx: PipelineContext) -> "np.ndarray | None":
    """The job's original left frame (its frame pair), BGR, or None."""
    import cv2
    from sqlalchemy import select

    from app.db_models import Artifact, ArtifactType
    from app.pipeline.interfaces import ctx_frame_index

    idx = ctx_frame_index(ctx)
    frame_filter = Artifact.frame_index == idx
    if idx == 0:  # legacy uploads have NULL frame_index
        frame_filter = frame_filter | Artifact.frame_index.is_(None)
    artifact = (await ctx.db_session.execute(
        select(Artifact)
        .where(
            Artifact.capture_session_id == ctx.capture_session_id,
            Artifact.artifact_type == ArtifactType.LEFT_FRAME,
            frame_filter,
        )
        .order_by(Artifact.frame_index)
        .limit(1)
    )).scalar_one_or_none()
    if artifact is None:
        return None
    resp = ctx.storage_client.get_object(
        Bucket=artifact.storage_bucket, Key=artifact.storage_key
    )
    arr = np.frombuffer(resp["Body"].read(), dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _downscale(img: "np.ndarray") -> "np.ndarray":
    import cv2

    h, w = img.shape[:2]
    if w <= MAX_VISUAL_WIDTH:
        return img
    scale = MAX_VISUAL_WIDTH / w
    return cv2.resize(img, (MAX_VISUAL_WIDTH, round(h * scale)), interpolation=cv2.INTER_AREA)


def render_mask_overlay(frame_bgr: "np.ndarray", masks: list[dict]) -> "np.ndarray":
    """Draw filled translucent polygons + outlines over the frame."""
    import cv2

    img = _downscale(frame_bgr).copy()
    h, w = img.shape[:2]
    fill = img.copy()
    rng = np.random.default_rng(seed=7)  # стабильные цвета между прогонами
    for mask in masks:
        poly = mask.get("polygon_normalized") or []
        if len(poly) < 3:
            continue
        pts = (np.array(poly, dtype=np.float64) * [w, h]).round().astype(np.int32)
        color = tuple(int(c) for c in rng.integers(60, 255, size=3))
        cv2.fillPoly(fill, [pts], color)
        cv2.polylines(img, [pts], isClosed=True, color=color, thickness=2)
    return cv2.addWeighted(fill, 0.35, img, 0.65, 0)


def render_depth_color(depth: "np.ndarray") -> "np.ndarray | None":
    """Normalize depth to its 2–98 percentile range and colorize; None if empty."""
    import cv2

    valid = np.isfinite(depth) & (depth > 0)
    if not valid.any():
        return None
    lo, hi = np.percentile(depth[valid], [2.0, 98.0])
    if hi <= lo:
        hi = lo + 1.0
    norm = np.clip((depth - lo) / (hi - lo), 0.0, 1.0)
    norm = np.where(valid, norm, 0.0)
    img = cv2.applyColorMap((norm * 255).astype(np.uint8), cv2.COLORMAP_JET)
    img[~valid] = (0, 0, 0)
    return _downscale(img)


class ReportVisualsStep(PipelineStep):
    step_name = "report_visuals"

    async def execute(self, ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult:
        import cv2

        t0 = time.monotonic()
        prefix = pipeline_prefix(ctx)
        base = f"{prefix}/report_visuals"
        overlay_key = f"{base}/mask_overlay.png"
        depth_key = f"{base}/depth_color.png"

        # Idempotency: overlay is written last → if it exists, the step already ran
        try:
            ctx.storage_client.head_object(Bucket=ctx.bucket_artifacts, Key=overlay_key)
            return StepResult(
                step_name=self.step_name, success=True,
                output_artifact_keys=[depth_key, overlay_key],
                duration_seconds=time.monotonic() - t0,
                metadata={"cached": True},
            )
        except Exception:
            pass

        produced: list[str] = []
        metadata: dict = {}

        def _put_png(key: str, img: "np.ndarray") -> None:
            ok, enc = cv2.imencode(".png", img)
            if not ok:
                raise ValueError("PNG encode failed")
            ctx.storage_client.put_object(
                Bucket=ctx.bucket_artifacts, Key=key,
                Body=enc.tobytes(), ContentType="image/png",
            )
            produced.append(key)

        # --- colorized depth -------------------------------------------------
        try:
            resp = ctx.storage_client.get_object(
                Bucket=ctx.bucket_artifacts, Key=f"{prefix}/depth_estimation/depth_map.npy"
            )
            depth = np.load(io.BytesIO(resp["Body"].read()))
            colored = render_depth_color(depth)
            if colored is not None:
                _put_png(depth_key, colored)
            else:
                metadata["depth_color"] = "skipped: no valid depth pixels"
        except Exception as exc:
            metadata["depth_color"] = f"skipped: {exc}"

        # --- mask overlay on the original left frame -------------------------
        try:
            frame = await _fetch_left_frame_bgr(ctx)
            if frame is None:
                metadata["mask_overlay"] = "skipped: no left frame artifact"
            else:
                resp = ctx.storage_client.get_object(
                    Bucket=ctx.bucket_artifacts, Key=f"{prefix}/segmentation/masks.json"
                )
                masks = json.loads(resp["Body"].read()).get("masks", [])
                _put_png(overlay_key, render_mask_overlay(frame, masks))
                metadata["n_masks_drawn"] = len(masks)
        except Exception as exc:
            metadata["mask_overlay"] = f"skipped: {exc}"

        return StepResult(
            step_name=self.step_name, success=True,  # visuals never fail the job
            output_artifact_keys=produced,
            duration_seconds=time.monotonic() - t0,
            metadata=metadata,
        )
