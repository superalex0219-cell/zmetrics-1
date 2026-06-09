---
paths:
  - "worker/**/*.py"
---

# Worker / Pipeline Rules

## Architecture
- All pipeline steps implement `PipelineStep` from `worker/app/pipeline/interfaces.py`
- Pipeline order:
  `calibration_load → rectification → depth_estimation → point_cloud → segmentation → particle_volumes → granulometry`
- Adding a step: implement `PipelineStep`, register it in `worker/app/tasks/pipeline.py`.
  Do NOT change the `Pipeline` or `PipelineContext` interface.

## Step contract
Every step MUST:
1. Accept `(ctx: PipelineContext, previous_results: list[StepResult]) -> StepResult`
2. Be idempotent: check if the output artifact already exists in MinIO before recomputing
3. Read inputs from MinIO; write outputs to MinIO (never the local filesystem)
4. Write outputs under: `sessions/{capture_session_id}/pipeline/{step_name}/`
5. Return `StepResult(success=False, error=str(exc))` on failure — **never raise**

## CV imports
- Do NOT import `cv2`, `open3d`, `ultralytics`, torch at module top-level in mock files
- Use conditional guards (`if TYPE_CHECKING: import cv2`) or import inside the method
- Real CV lives in `worker/app/pipeline/cv_*.py` and ML steps (e.g. `sam3_segmentation.py`);
  these do NOT replace the mock files — selection is by feature flag + frame availability

## Celery task rules
- Check `job.status == 'completed'` before processing (idempotency) and return early
- Set `status = 'running'`, `started_at = now()` before the pipeline runs
- Set `status = 'completed'`, `completed_at = now()` + save `pipeline_log` on success
- Catch ALL exceptions → set `status = 'failed'`, `error_message = str(exc)`
- Use `asyncio.run(_async_impl())` at the sync task boundary
- On Windows: `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())` first

## Pipeline log
Each step appends to `analysis_job.pipeline_log` (JSONB):
`{"step": name, "status": "ok"|"error", "duration_s": float, "artifacts": [...]}`.
Save the full log on completion.

## Mock vs real
- Mock steps generate plausible synthetic domain data:
  - Particle diameters: log-normal, mean ~250mm, sigma ~log(1.8)
  - Depth range: 2.0m–8.0m; point cloud: 5000–20000 points in a 10×10×3m volume
  - Segmentation: 80–200 particles/image; confidence: 0.65–0.85
- `mock_granulometry.py` (final step) creates the `AnalysisResult` row with synthetic
  P10/P50/P80; `confidence_notes` must say `"mock pipeline — values are synthetic, not from real CV"`
- Mock step duration simulated with `asyncio.sleep(0.1)`

## Scientific integrity
- Never round/truncate P10/P50/P80 in computation — full float precision
- Always include `confidence_score` and `confidence_notes`
- Rosin-Rammler fit failures: log in `StepResult.metadata`, never silently ignore
- Rules engine (`app/rules.py`) is a pure function — never applies parameters; suggestions
  are reference only (see `safety.md`)

## DB access from worker
- Worker uses `worker/app/db_models.py` (minimal model stubs) — keep in sync with
  `backend/app/db/models/`. Adding a column to `AnalysisJob`/`AnalysisResult` → update both.
