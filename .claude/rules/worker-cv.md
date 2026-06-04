---
paths:
  - "worker/**/*.py"
---

# Worker / CV-ML Rules

## Pipeline architecture

Steps implement `PipelineStep` from `worker/app/pipeline/interfaces.py`. Order:
```
calibration_load → rectification → depth_estimation → point_cloud
→ segmentation → particle_volumes → granulometry
```

Adding a new step: implement `PipelineStep`, register it in `worker/app/tasks/pipeline.py`. Do not change the `Pipeline` or `PipelineContext` interface.

## Step contract

Every step MUST:
1. Accept `(ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult`
2. Be idempotent: check if output artifact exists in MinIO before recomputing
3. Read inputs from MinIO; write outputs to MinIO (never to local filesystem)
4. Return `StepResult(success=False, error=str(exc))` on failure — never raise
5. Write outputs under: `sessions/{capture_session_id}/pipeline/{step_name}/`

## Celery task rules

- Check `job.status == 'completed'` before processing (idempotency)
- Set `status = 'running'`, `started_at = now()` before pipeline runs
- Set `status = 'completed'`, `completed_at = now()` + save `pipeline_log` on success
- Set `status = 'failed'`, `error_message = str(exc)` on any unhandled exception
- Use `asyncio.run(_async_impl())` at the sync task boundary (stable cross-platform)
- On Windows: `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())` before `asyncio.run()`

## CV imports

- Do NOT import `cv2`, `open3d`, `ultralytics` at module top-level in mock files
- Use conditional guard: `if TYPE_CHECKING: import cv2`
- Real CV implementations go in `worker/app/pipeline/cv_*.py` (not replacing mock files)

## Mock step values

Mock steps generate plausible synthetic data for the quarry domain:
- Particle diameters: log-normal, mean ~250mm, sigma ~log(1.8)
- Depth range: 2.0m – 8.0m
- Point cloud: 5000–20000 points in a 10×10×3m volume
- Segmentation: 80–200 particles per image
- Confidence: 0.65–0.85 (mocks are honest about being mocks)

## DB access from worker

Worker uses `worker/app/db_models.py` (minimal model stubs). These must stay in sync with `backend/app/db/models/`. When adding a new column to `AnalysisJob` or `AnalysisResult`, update both files.

## Scientific integrity

- Never round or truncate P10/P50/P80 in computation — full float precision
- Always include `confidence_score` and `confidence_notes` in mock results
- `confidence_notes` for mocks must say: `"mock pipeline — values are synthetic, not from real CV"`
- Rosin-Rammler fit failures must be logged in `StepResult.metadata`, not silently ignored
