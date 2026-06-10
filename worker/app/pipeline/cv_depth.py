"""Real step: stereo depth estimation via StereoSGBM."""
import io
import json
import time

import numpy as np

from app.pipeline.interfaces import PipelineContext, PipelineStep, StepResult


class CVStereoDepthStep(PipelineStep):
    step_name = "depth_estimation"

    # StereoSGBM parameters (tuned for ZED 2 at 1280x720)
    NUM_DISPARITIES = 128   # must be divisible by 16
    BLOCK_SIZE = 9
    MIN_DISPARITY = 0

    async def execute(self, ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult:
        import cv2
        t0 = time.monotonic()
        base = f"sessions/{ctx.capture_session_id}/pipeline/depth_estimation"
        depth_key = f"{base}/depth_map.npy"
        disp_key = f"{base}/disparity.npy"

        # Idempotency
        try:
            ctx.storage_client.head_object(Bucket=ctx.bucket_artifacts, Key=depth_key)
            return StepResult(
                step_name=self.step_name, success=True,
                output_artifact_keys=[depth_key, disp_key],
                duration_seconds=time.monotonic() - t0,
                metadata={"cached": True},
            )
        except Exception:
            pass

        try:
            rect_base = f"sessions/{ctx.capture_session_id}/pipeline/rectification"

            def _read_image(key: str) -> np.ndarray:
                resp = ctx.storage_client.get_object(Bucket=ctx.bucket_artifacts, Key=key)
                arr = np.frombuffer(resp["Body"].read(), dtype=np.uint8)
                return cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)

            gray_l = _read_image(f"{rect_base}/rectified_left.jpg")
            gray_r = _read_image(f"{rect_base}/rectified_right.jpg")

            sgbm = cv2.StereoSGBM_create(
                minDisparity=self.MIN_DISPARITY,
                numDisparities=self.NUM_DISPARITIES,
                blockSize=self.BLOCK_SIZE,
                P1=8 * 3 * self.BLOCK_SIZE ** 2,
                P2=32 * 3 * self.BLOCK_SIZE ** 2,
                disp12MaxDiff=1,
                uniquenessRatio=10,
                speckleWindowSize=100,
                speckleRange=32,
                preFilterCap=63,
                mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY,
            )
            disparity = sgbm.compute(gray_l, gray_r).astype(np.float32) / 16.0

            # Load Q matrix from rectification step
            q_resp = ctx.storage_client.get_object(
                Bucket=ctx.bucket_artifacts,
                Key=f"{rect_base}/Q_matrix.json",
            )
            Q = np.array(json.loads(q_resp["Body"].read())["Q"], dtype=np.float64)

            # Disparity → 3D points via Q matrix
            points_3d = cv2.reprojectImageTo3D(disparity, Q)

            # Extract depth channel (Z), clip invalid (<0 or inf)
            depth_map = points_3d[:, :, 2]
            depth_map = np.where(
                (disparity <= 0) | (~np.isfinite(depth_map)) | (depth_map <= 0),
                np.nan,
                depth_map,
            )

            def _upload_npy(key: str, arr: np.ndarray) -> None:
                buf = io.BytesIO()
                np.save(buf, arr)
                buf.seek(0)
                ctx.storage_client.put_object(
                    Bucket=ctx.bucket_artifacts, Key=key,
                    Body=buf.getvalue(), ContentType="application/octet-stream",
                )

            _upload_npy(depth_key, depth_map)
            _upload_npy(disp_key, disparity)

            valid_pixels = int(np.sum(np.isfinite(depth_map)))
            median_depth = float(np.nanmedian(depth_map)) if valid_pixels > 0 else 0.0

            return StepResult(
                step_name=self.step_name, success=True,
                output_artifact_keys=[depth_key, disp_key],
                duration_seconds=time.monotonic() - t0,
                metadata={
                    "valid_pixels": valid_pixels,
                    "median_depth_m": round(median_depth, 3),
                    "num_disparities": self.NUM_DISPARITIES,
                    "block_size": self.BLOCK_SIZE,
                },
            )

        except Exception as exc:
            return StepResult(
                step_name=self.step_name, success=False,
                output_artifact_keys=[],
                duration_seconds=time.monotonic() - t0,
                error=str(exc),
            )
