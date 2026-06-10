# WORKER-FIX-1 — Fix worker db_models.py stubs + SAM3 artifact read

**Date:** 2026-06-08  
**Layer:** `worker/app/db_models.py` + `worker/app/pipeline/sam3_segmentation.py`  
**Prerequisite for:** WEB-ANALYSIS-1, M2-stereo  
**Review agent:** `cv-pipeline-reviewer`  
**Estimated scope:** ~30 min

---

## Problem

Two bugs block the full end-to-end pipeline job:

### Bug 1 — Artifact stub has wrong column name

`worker/app/db_models.py` `Artifact` model declares:
```python
minio_key: Mapped[str] = mapped_column(String(1000), nullable=False)
```
The real `artifact` table (see `backend/app/db/models/artifact.py`) has:
```python
storage_bucket: Mapped[str]  # column name: storage_bucket
storage_key: Mapped[str]     # column name: storage_key
```
`minio_key` does not exist. Any SELECT that loads `Artifact` objects will raise a DB column error at runtime.

### Bug 2 — SAM3 step reads wrong field + wrong bucket

`worker/app/pipeline/sam3_segmentation.py` uses:
```python
ctx.storage_client.get_object(Bucket=ctx.bucket_frames, Key=artifact.minio_key)
```
Should be:
```python
ctx.storage_client.get_object(Bucket=artifact.storage_bucket, Key=artifact.storage_key)
```
Also hardcoding `ctx.bucket_frames` is wrong — artifact could be in either bucket depending on upload.

### Bug 3 — CaptureSession stub missing `calibration_id`

Real `capture_session` table has `calibration_id UUID NOT NULL`. The worker stub omits it. Needed for M2 `CVCalibrationStep`.

---

## Changes

### `worker/app/db_models.py`

**Replace** the `Artifact` class body:
```python
class Artifact(Base):
    """Read-only stub: worker reads frames for pipeline steps."""
    __tablename__ = "artifact"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    capture_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    artifact_type: Mapped[ArtifactType] = mapped_column(
        SAEnum(ArtifactType, name="artifact_type", create_type=False), nullable=False
    )
    storage_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    frame_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

**Replace** the `CaptureSession` class body (add `calibration_id`):
```python
class CaptureSession(Base):
    __tablename__ = "capture_session"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    blast_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    captured_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    calibration_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
```

**Add** a new `Calibration` stub after `CaptureSession` (needed for M2, safe to add now):
```python
class Calibration(Base):
    """Read-only stub: worker reads calibration matrices for real stereo CV steps."""
    __tablename__ = "calibration"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    left_camera_matrix: Mapped[dict] = mapped_column(JSONB, nullable=False)
    right_camera_matrix: Mapped[dict] = mapped_column(JSONB, nullable=False)
    left_dist_coeffs: Mapped[dict] = mapped_column(JSONB, nullable=False)
    right_dist_coeffs: Mapped[dict] = mapped_column(JSONB, nullable=False)
    rotation_matrix: Mapped[dict] = mapped_column(JSONB, nullable=False)
    translation_vector: Mapped[dict] = mapped_column(JSONB, nullable=False)
    baseline_mm: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    image_width_px: Mapped[int] = mapped_column(Integer, nullable=False)
    image_height_px: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
```

### `worker/app/pipeline/sam3_segmentation.py`

Find the line:
```python
resp = ctx.storage_client.get_object(
    Bucket=ctx.bucket_frames, Key=artifact.minio_key
)
```
Replace with:
```python
resp = ctx.storage_client.get_object(
    Bucket=artifact.storage_bucket, Key=artifact.storage_key
)
```

Also find the warning log:
```python
logger.warning(
    "sam3_frame_download_failed",
    extra={"minio_key": artifact.minio_key, "error": str(exc)},
)
```
Replace with:
```python
logger.warning(
    "sam3_frame_download_failed",
    extra={"storage_key": artifact.storage_key, "error": str(exc)},
)
```

---

## Tests

Run existing worker tests — all should still pass (no test logic changes):
```powershell
docker compose -f infra\docker-compose.yml exec worker pytest worker/tests -v
```

Expected: same number of tests pass as before (23).

---

## Acceptance criteria

- [ ] `worker/app/db_models.py`: `Artifact` has `storage_bucket` + `storage_key` (no `minio_key`)
- [ ] `worker/app/db_models.py`: `CaptureSession` has `calibration_id` + `device_id`
- [ ] `worker/app/db_models.py`: `Calibration` stub added
- [ ] `sam3_segmentation.py`: reads `artifact.storage_bucket` + `artifact.storage_key`
- [ ] Worker tests still pass
