"""Real step: 3D point cloud from depth map via cv2.reprojectImageTo3D."""
import io
import json
import time

import numpy as np

from app.pipeline.interfaces import PipelineContext, PipelineStep, StepResult, pipeline_prefix


class CVPointCloudStep(PipelineStep):
    step_name = "point_cloud"

    async def execute(self, ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult:
        t0 = time.monotonic()
        base = f"{pipeline_prefix(ctx)}/point_cloud"
        cloud_key = f"{base}/cloud.npy"

        # Idempotency
        try:
            ctx.storage_client.head_object(Bucket=ctx.bucket_artifacts, Key=cloud_key)
            return StepResult(
                step_name=self.step_name, success=True,
                output_artifact_keys=[cloud_key],
                duration_seconds=time.monotonic() - t0,
                metadata={"cached": True},
            )
        except Exception:
            pass

        try:
            depth_key = f"{pipeline_prefix(ctx)}/depth_estimation/depth_map.npy"
            resp = ctx.storage_client.get_object(Bucket=ctx.bucket_artifacts, Key=depth_key)
            depth_map = np.load(io.BytesIO(resp["Body"].read()))

            # Load calibration to get fx, fy, cx, cy for back-projection
            cal_resp = ctx.storage_client.get_object(
                Bucket=ctx.bucket_artifacts,
                Key=f"{pipeline_prefix(ctx)}/calibration_params.json",
            )
            cal = json.loads(cal_resp["Body"].read())
            m = cal["left_camera_matrix"]
            fx, fy, cx, cy = m["fx"], m["fy"], m["cx"], m["cy"]

            h, w = depth_map.shape
            uu, vv = np.meshgrid(np.arange(w), np.arange(h))
            valid = np.isfinite(depth_map) & (depth_map > 0)

            z = depth_map[valid]
            x = (uu[valid] - cx) * z / fx
            y = (vv[valid] - cy) * z / fy

            cloud = np.stack([x, y, z], axis=1).astype(np.float32)

            buf = io.BytesIO()
            np.save(buf, cloud)
            buf.seek(0)
            ctx.storage_client.put_object(
                Bucket=ctx.bucket_artifacts, Key=cloud_key,
                Body=buf.getvalue(), ContentType="application/octet-stream",
            )

            return StepResult(
                step_name=self.step_name, success=True,
                output_artifact_keys=[cloud_key],
                duration_seconds=time.monotonic() - t0,
                metadata={"n_points": len(cloud)},
            )

        except Exception as exc:
            return StepResult(
                step_name=self.step_name, success=False,
                output_artifact_keys=[],
                duration_seconds=time.monotonic() - t0,
                error=str(exc),
            )
