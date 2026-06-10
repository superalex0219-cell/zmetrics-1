# M2-STEREO — Real OpenCV Stereo CV Pipeline в worker

**Date:** 2026-06-08  
**Layer:** `worker/app/pipeline/cv_*.py` (новые файлы) + `worker/app/tasks/pipeline.py` (регистрация) + `worker/pyproject.toml` (зависимости)  
**Prerequisite:** WORKER-FIX-1 выполнен (Artifact stub исправлен, Calibration stub добавлен)  
**Review agent:** `cv-pipeline-reviewer` + `security-reviewer` (нет path traversal в MinIO-ключах)

---

## Goal

Заменить mock-шаги глубины и облака точек реальными OpenCV-шагами.  
ZED 2 используется как обычная стереокамера — **без ZED SDK**.  
Глубина вычисляется через диспаратность пикселей (StereoSGBM).

Pipeline после задачи:
```
cv_calibration_load → cv_rectification → cv_stereo_depth → cv_point_cloud
→ Sam3SegmentationStep (без изменений)
→ MockParticleVolumeStep (без изменений, до M3)
→ MockGranulometryStep (без изменений, до M3)
```

Запуск реальных CV-шагов: только когда `ENABLE_REAL_STEREO=true` (env var) **И** в CaptureSession есть оба артефакта `left_frame` + `right_frame`. Если условие не выполнено — pipeline использует mock-шаги (обратная совместимость).

---

## Acceptance criteria

- [ ] `ENABLE_REAL_STEREO=false` → pipeline использует те же mock-шаги (все существующие тесты проходят)
- [ ] `ENABLE_REAL_STEREO=true` + только `left_frame` → pipeline использует mock-шаги (SAM3 уже реальный)
- [ ] `ENABLE_REAL_STEREO=true` + `left_frame` + `right_frame` → cv-шаги запускаются, `depth_map` → MinIO, `point_cloud` → MinIO
- [ ] `cv_calibration_load`: читает `Calibration` из DB по `capture_session.calibration_id`
- [ ] `cv_rectification`: использует `cv2.stereoRectify` + `cv2.initUndistortRectifyMap` + `cv2.remap`
- [ ] `cv_stereo_depth`: использует `cv2.StereoSGBM_create`; depth_map в npy формате
- [ ] `cv_point_cloud`: использует `cv2.reprojectImageTo3D`; облако точек в npy формате
- [ ] Все шаги идемпотентны (проверка MinIO перед пересчётом)
- [ ] На ошибку: `StepResult(success=False, error=str(exc))`, никогда не raise
- [ ] `pyproject.toml` worker: добавлены `opencv-python-headless` + `numpy` (могут уже быть)

---

## Зависимости (`worker/pyproject.toml`)

```toml
[project.optional-dependencies]
stereo = [
    "opencv-python-headless>=4.10",
]
```

Добавить `stereo` в базовые зависимости, или установить всегда (вместе с `sam3`):
```toml
dependencies = [
    # ... existing ...
    "opencv-python-headless>=4.10",
]
```

> OpenCV 4.x уже в образе скорее всего (SAM3 `sam3_segmentation.py` импортирует `import cv2` в `_convert_to_mask_format`). Проверить Dockerfile перед добавлением.

---

## Конфигурация (`worker/app/config.py`)

Добавить поле:
```python
enable_real_stereo: bool = Field(default=False, alias="ENABLE_REAL_STEREO")
```

---

## Новые файлы

### `worker/app/pipeline/cv_calibration.py`

```python
"""Real step: load calibration from DB and write as JSON to MinIO."""
import json
import time
from uuid import UUID

import numpy as np

from app.pipeline.interfaces import PipelineContext, PipelineStep, StepResult


class CVCalibrationStep(PipelineStep):
    step_name = "calibration_load"

    async def execute(self, ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult:
        t0 = time.monotonic()
        output_key = f"sessions/{ctx.capture_session_id}/pipeline/calibration_params.json"

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
```

### `worker/app/pipeline/cv_rectification.py`

```python
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
    return np.array(d["data"], dtype=np.float64)


def _load_frame(ctx: PipelineContext, artifact_type: str) -> np.ndarray | None:
    """Load a frame artifact from MinIO. Returns None if not found."""
    import cv2
    from sqlalchemy import select
    from app.db_models import Artifact, ArtifactType

    # Synchronous DB query — called from async context via asyncio.run already in task
    # Use sync wrapper pattern: caller must be inside asyncio.run()
    # We use ctx.db_session (AsyncSession) — must await, but this function is called
    # from an async step. Use a helper coroutine instead.
    raise NotImplementedError("Use _load_frame_async instead")


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
```

### `worker/app/pipeline/cv_depth.py`

```python
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
```

### `worker/app/pipeline/cv_pointcloud.py`

```python
"""Real step: 3D point cloud from depth map via cv2.reprojectImageTo3D."""
import io
import json
import time

import numpy as np

from app.pipeline.interfaces import PipelineContext, PipelineStep, StepResult


class CVPointCloudStep(PipelineStep):
    step_name = "point_cloud"

    async def execute(self, ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult:
        t0 = time.monotonic()
        base = f"sessions/{ctx.capture_session_id}/pipeline/point_cloud"
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
            depth_key = f"sessions/{ctx.capture_session_id}/pipeline/depth_estimation/depth_map.npy"
            resp = ctx.storage_client.get_object(Bucket=ctx.bucket_artifacts, Key=depth_key)
            depth_map = np.load(io.BytesIO(resp["Body"].read()))

            # Load calibration to get fx, fy, cx, cy for back-projection
            cal_resp = ctx.storage_client.get_object(
                Bucket=ctx.bucket_artifacts,
                Key=f"sessions/{ctx.capture_session_id}/pipeline/calibration_params.json",
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
```

---

## Изменения в `worker/app/tasks/pipeline.py`

Добавить логику выбора шагов на основе `ENABLE_REAL_STEREO` + наличия `right_frame`.

В функции `_run_pipeline_async`, **заменить** блок `pipeline = Pipeline([...])` на:

```python
# Determine whether to use real stereo CV steps
use_real_stereo = settings.enable_real_stereo and await _has_right_frame(db, job.capture_session_id)

if use_real_stereo:
    from app.pipeline.cv_calibration import CVCalibrationStep
    from app.pipeline.cv_rectification import CVRectificationStep
    from app.pipeline.cv_depth import CVStereoDepthStep
    from app.pipeline.cv_pointcloud import CVPointCloudStep
    calibration_step = CVCalibrationStep()
    rectification_step = CVRectificationStep()
    depth_step = CVStereoDepthStep()
    pointcloud_step = CVPointCloudStep()
else:
    calibration_step = MockCalibrationStep()
    rectification_step = MockRectificationStep()
    depth_step = MockDepthStep()
    pointcloud_step = MockPointCloudStep()

pipeline = Pipeline([
    calibration_step,
    rectification_step,
    depth_step,
    pointcloud_step,
    Sam3SegmentationStep(
        model_path=settings.sam3_model_path,
        text_prompt=settings.sam3_text_prompt,
        threshold=settings.sam3_confidence_threshold,
    ),
    MockParticleVolumeStep(),
    MockGranulometryStep(),
])
```

Добавить helper функцию:

```python
async def _has_right_frame(db, capture_session_id: UUID) -> bool:
    """Check if capture session has a right_frame artifact."""
    from sqlalchemy import select
    from app.db_models import Artifact, ArtifactType
    result = await db.execute(
        select(Artifact).where(
            Artifact.capture_session_id == capture_session_id,
            Artifact.artifact_type == ArtifactType.RIGHT_FRAME,
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None
```

---

## Конфигурация `infra/docker-compose.yml`

В `worker` service environment добавить:
```yaml
ENABLE_REAL_STEREO: ${ENABLE_REAL_STEREO:-false}
```

В `infra/.env.example` добавить:
```
# Set to true to use OpenCV StereoSGBM instead of mock depth estimation.
# Requires both left_frame and right_frame artifacts in each CaptureSession.
ENABLE_REAL_STEREO=false
```

---

## Тесты

Добавить в `worker/tests/` файл `test_cv_pipeline.py`:
```python
"""Unit tests for CV pipeline steps (no real camera, no GPU required)."""
import pytest
# Test CVCalibrationStep with mock DB that returns a Calibration row
# Test CVStereoDepthStep with synthetic rectified image pair (np.zeros)
# Test _has_right_frame returns True/False correctly
# Test pipeline.py selects mock steps when ENABLE_REAL_STEREO=false
```

> Минимум 5 unit-тестов. Не требуют реального ZED 2 — используют синтетические изображения (np.random).

---

## Safety / invariants

- CV-шаги: `success=False` + `error=str(exc)` при любом исключении — **никогда не raise**
- Все выходные ключи MinIO: `sessions/{capture_session_id}/pipeline/...` — только UUID в пути (нет user input)
- Параметры StereoSGBM захардкожены — не из user input (нет injection)
- Калибровочные матрицы берутся из DB (проверены backend validation) — не из запроса

---

## Checklist для review-агента

- [ ] `cv_*.py` импортируют `cv2` только внутри функций (не на уровне модуля)
- [ ] Все 4 шага идемпотентны (head_object перед вычислением)
- [ ] `_has_right_frame` не вызывается если `ENABLE_REAL_STEREO=false`
- [ ] Существующие тесты (23) по-прежнему проходят при `ENABLE_REAL_STEREO=false`
- [ ] MinIO ключи: только `str(UUID)` в пути — нет переменных из user input
- [ ] `depth_map.npy` хранит float32, не int16
- [ ] Q-матрица сохраняется в rectification и читается в depth step (нет дублирования вычисления)
