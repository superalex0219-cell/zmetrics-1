"""Real step: stereo rectification via OpenCV."""
import io
import json
import time

import numpy as np

from app.pipeline.interfaces import PipelineContext, PipelineStep, StepResult


def _load_calibration_from_minio(ctx: PipelineContext) -> dict:
    """Read calibration_params.json written by CVCalibrationStep."""
    key = f"sessions/{ctx.capture_session_id}/pipeline/calibration_params.json"
    resp = ctx.storage_client.get_object(Bucket=ctx.bucket_artifacts, Key=key)
    return json.loads(resp["Body"].read())


def _dict_to_camera_matrix(d: dict) -> np.ndarray:
    return np.array([[d["fx"], 0, d["cx"]], [0, d["fy"], d["cy"]], [0, 0, 1]], dtype=np.float64)


def _dict_to_dist(d: dict) -> np.ndarray:
    return np.array([d["k1"], d["k2"], d["p1"], d["p2"], d.get("k3", 0.0)], dtype=np.float64)


def _dict_to_matrix(d: dict) -> np.ndarray:
    """Matrix from ``{rows, cols, data}`` where data may be nested or flat.

    Clients store JSONB matrices in both shapes (the desktop test-device stub
    uses a flat 9-element list) — reshape instead of crashing inside
    cv2.stereoRectify/Rodrigues with "srcSz is [1 x 9]".
    """
    arr = np.array(d["data"], dtype=np.float64)
    rows, cols = d.get("rows"), d.get("cols")
    if rows and cols:
        return arr.reshape(int(rows), int(cols))
    if arr.ndim == 1:
        if arr.size == 9:
            return arr.reshape(3, 3)
        if arr.size == 3:
            return arr.reshape(3, 1)
    return arr


async def _load_frame_async(ctx: PipelineContext, artifact_type_str: str) -> np.ndarray | None:
    """Async: load a frame artifact from MinIO."""
    import cv2
    from sqlalchemy import select
    from app.db_models import Artifact, ArtifactType

    artifact_type = ArtifactType(artifact_type_str)
    result = await ctx.db_session.execute(
        select(Artifact)
        .where(
            Artifact.capture_session_id == ctx.capture_session_id,
            Artifact.artifact_type == artifact_type,
        )
        .limit(1)
    )
    artifact = result.scalar_one_or_none()
    if artifact is None:
        return None

    resp = ctx.storage_client.get_object(
        Bucket=artifact.storage_bucket, Key=artifact.storage_key
    )
    image_bytes = resp["Body"].read()
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


class CVRectificationStep(PipelineStep):
    step_name = "rectification"

    async def execute(self, ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult:
        import cv2
        t0 = time.monotonic()
        base = f"sessions/{ctx.capture_session_id}/pipeline/rectification"
        left_key = f"{base}/rectified_left.jpg"
        right_key = f"{base}/rectified_right.jpg"

        # Idempotency
        try:
            ctx.storage_client.head_object(Bucket=ctx.bucket_artifacts, Key=left_key)
            return StepResult(
                step_name=self.step_name, success=True,
                output_artifact_keys=[left_key, right_key],
                duration_seconds=time.monotonic() - t0,
                metadata={"cached": True},
            )
        except Exception:
            pass

        try:
            cal = _load_calibration_from_minio(ctx)
            K_l = _dict_to_camera_matrix(cal["left_camera_matrix"])
            K_r = _dict_to_camera_matrix(cal["right_camera_matrix"])
            D_l = _dict_to_dist(cal["left_dist_coeffs"])
            D_r = _dict_to_dist(cal["right_dist_coeffs"])
            R = _dict_to_matrix(cal["rotation_matrix"])
            T = _dict_to_matrix(cal["translation_vector"]).reshape(3, 1)
            w, h = cal["image_width_px"], cal["image_height_px"]

            img_l = await _load_frame_async(ctx, "left_frame")
            img_r = await _load_frame_async(ctx, "right_frame")
            if img_l is None or img_r is None:
                raise ValueError("Both left_frame and right_frame required for real rectification")

            R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K_l, D_l, K_r, D_r, (w, h), R, T, alpha=0)
            map1_l, map2_l = cv2.initUndistortRectifyMap(K_l, D_l, R1, P1, (w, h), cv2.CV_16SC2)
            map1_r, map2_r = cv2.initUndistortRectifyMap(K_r, D_r, R2, P2, (w, h), cv2.CV_16SC2)

            rect_l = cv2.remap(img_l, map1_l, map2_l, cv2.INTER_LINEAR)
            rect_r = cv2.remap(img_r, map1_r, map2_r, cv2.INTER_LINEAR)

            for key, img in [(left_key, rect_l), (right_key, rect_r)]:
                _, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                ctx.storage_client.put_object(
                    Bucket=ctx.bucket_artifacts, Key=key,
                    Body=enc.tobytes(), ContentType="image/jpeg",
                )

            # Persist Q matrix for depth step
            q_key = f"{base}/Q_matrix.json"
            ctx.storage_client.put_object(
                Bucket=ctx.bucket_artifacts, Key=q_key,
                Body=json.dumps({"Q": Q.tolist()}).encode(),
                ContentType="application/json",
            )

            return StepResult(
                step_name=self.step_name, success=True,
                output_artifact_keys=[left_key, right_key, q_key],
                duration_seconds=time.monotonic() - t0,
                metadata={"width": w, "height": h},
            )

        except Exception as exc:
            return StepResult(
                step_name=self.step_name, success=False,
                output_artifact_keys=[],
                duration_seconds=time.monotonic() - t0,
                error=str(exc),
            )
