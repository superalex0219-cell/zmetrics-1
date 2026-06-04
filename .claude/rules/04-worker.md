---
paths:
  - "worker/**/*.py"
---

# Worker / Pipeline Rules

## Architecture
- All pipeline steps implement `PipelineStep` ABC from `worker/app/pipeline/interfaces.py`
- Pipeline: `calibration_load → rectification → depth_estimation → point_cloud → segmentation → particle_volumes → granulometry`
- Each step: reads inputs from MinIO, writes outputs to MinIO, returns `StepResult`

## Step Implementation Rules
- Steps must be idempotent: check if output artifact already exists before recomputing
- Never import `cv2`, `open3d`, or other heavy CV libs at module top-level in mock files — use conditional guards
- Each step writes its output artifacts under: `sessions/{capture_session_id}/pipeline/{step_name}/`
- Step duration should be simulated with `asyncio.sleep(0.1)` in mocks

## Celery Task Rules
- Tasks must catch ALL exceptions and set `analysis_job.status = 'failed'` with `error_message = str(exc)`
- Before processing, check `analysis_job.status == 'completed'` and return early if so (idempotency)
- Use `asyncio.run(_async_impl())` inside the sync Celery task to run async pipeline code
- Set `analysis_job.status = 'running'` and `started_at = now()` at the start of processing
- Set `analysis_job.status = 'completed'` and `completed_at = now()` on success

## Pipeline Log
- Each step appends to `analysis_job.pipeline_log` (JSONB): `{"step": name, "status": "ok"|"error", "duration_s": float, "artifacts": [...]}`
- On completion, save full log to `analysis_job.pipeline_log`

## Mock vs Real
- Mock steps produce synthetic data (random but plausible values)
- `mock_granulometry.py` final step: creates `AnalysisResult` record in DB with synthetic P10/P50/P80 from log-normal distribution (mean ~250mm, std ~100mm for a typical blast)
- Real CV implementations will live in `pipeline/cv_*.py` files, not replacing mocks
