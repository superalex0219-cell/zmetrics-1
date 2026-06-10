"""Real step: load calibration from DB and write as JSON to MinIO."""
import json
import time

import numpy as np

from app.pipeline.interfaces import PipelineContext, PipelineStep, StepResult, pipeline_prefix


class CVCalibrationStep(PipelineStep):
    step_name = "calibration_load"

    async def execute(self, ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult:
        t0 = time.monotonic()
        output_key = f"{pipeline_prefix(ctx)}/calibration_params.json"

        # Idempotency: skip if already written
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
            from sqlalchemy import select
            from app.db_models import CaptureSession, Calibration

            session_row = (await ctx.db_session.execute(
                select(CaptureSession).where(CaptureSession.id == ctx.capture_session_id)
            )).scalar_one_or_none()
            if session_row is None:
                raise ValueError(f"CaptureSession {ctx.capture_session_id} not found")

            cal_row = (await ctx.db_session.execute(
                select(Calibration).where(Calibration.id == session_row.calibration_id)
            )).scalar_one_or_none()
            if cal_row is None:
                raise ValueError(f"Calibration {session_row.calibration_id} not found")

            # Fail fast on stub calibrations (identity camera matrix, fx=1.0):
            # the real stereo path would silently produce garbage metric depth.
            fx = float(cal_row.left_camera_matrix.get("fx", 0.0))
            fy = float(cal_row.left_camera_matrix.get("fy", 0.0))
            if fx < 50.0 or fy < 50.0:
                raise ValueError(
                    f"Calibration {cal_row.id} looks like a test stub "
                    f"(fx={fx:g}, fy={fy:g} px) — real stereo needs a real camera "
                    "calibration. Register the ZED factory calibration "
                    "(кнопка «Зарегистрировать ZED» на экране съёмки)."
                )

            params = {
                "source": "opencv",
                "baseline_mm": float(cal_row.baseline_mm),
                "image_width_px": cal_row.image_width_px,
                "image_height_px": cal_row.image_height_px,
                "left_camera_matrix": cal_row.left_camera_matrix,
                "right_camera_matrix": cal_row.right_camera_matrix,
                "left_dist_coeffs": cal_row.left_dist_coeffs,
                "right_dist_coeffs": cal_row.right_dist_coeffs,
                "rotation_matrix": cal_row.rotation_matrix,
                "translation_vector": cal_row.translation_vector,
            }

            ctx.storage_client.put_object(
                Bucket=ctx.bucket_artifacts,
                Key=output_key,
                Body=json.dumps(params).encode(),
                ContentType="application/json",
            )

            return StepResult(
                step_name=self.step_name, success=True,
                output_artifact_keys=[output_key],
                duration_seconds=time.monotonic() - t0,
                metadata={"baseline_mm": params["baseline_mm"], "source": "db"},
            )

        except Exception as exc:
            return StepResult(
                step_name=self.step_name, success=False,
                output_artifact_keys=[],
                duration_seconds=time.monotonic() - t0,
                error=str(exc),
            )
