"""Celery task: run the full analysis pipeline for an AnalysisJob."""

import asyncio
import sys
from datetime import datetime, timezone
from uuid import UUID

import structlog

from app.celery_app import celery

logger = structlog.get_logger()


@celery.task(bind=True, name="worker.tasks.pipeline.run_pipeline", max_retries=0)
def run_pipeline(self, job_id: str) -> dict:
    """
    Main Celery task. Orchestrates the full mock CV/ML pipeline.

    Idempotent: if the job is already completed, returns early.
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    return asyncio.run(_run_pipeline_async(UUID(job_id)))


async def _run_pipeline_async(job_id: UUID) -> dict:
    import boto3
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.pipeline.interfaces import Pipeline, PipelineContext, PipelineStepError
    from app.pipeline.mock_calibration import MockCalibrationStep
    from app.pipeline.mock_depth import MockDepthStep
    from app.pipeline.mock_granulometry import MockGranulometryStep
    from app.pipeline.mock_particles import MockParticleVolumeStep
    from app.pipeline.mock_pointcloud import MockPointCloudStep
    from app.pipeline.mock_rectification import MockRectificationStep
    from app.pipeline.mock_segmentation import MockSegmentationStep

    settings = get_settings()

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        job = await _load_job(db, job_id)
        if job is None:
            logger.error("pipeline_job_not_found", job_id=str(job_id))
            return {"status": "not_found"}

        if job.status.value == "completed":
            logger.info("pipeline_already_completed", job_id=str(job_id))
            return {"status": "already_completed"}

        # Mark as running
        job.status = _JobStatus("running")
        job.started_at = datetime.now(tz=timezone.utc)
        await db.commit()

        # Build S3 client
        s3_client = boto3.client(
            "s3",
            endpoint_url=f"http{'s' if settings.minio_use_ssl else ''}://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
        )

        ctx = PipelineContext(
            job_id=job_id,
            capture_session_id=job.capture_session_id,
            storage_client=s3_client,
            db_session=db,
            bucket_frames=settings.minio_bucket_frames,
            bucket_artifacts=settings.minio_bucket_artifacts,
        )

        pipeline = Pipeline([
            MockCalibrationStep(),
            MockRectificationStep(),
            MockDepthStep(),
            MockPointCloudStep(),
            MockSegmentationStep(),
            MockParticleVolumeStep(),
            MockGranulometryStep(),
        ])

        try:
            step_results = await pipeline.run(ctx)

            pipeline_log = {
                "steps": [
                    {
                        "name": r.step_name,
                        "status": "ok" if r.success else "error",
                        "duration_s": round(r.duration_seconds, 3),
                        "artifacts": r.output_artifact_keys,
                        "metadata": r.metadata,
                    }
                    for r in step_results
                ]
            }

            job.status = _JobStatus("completed")
            job.completed_at = datetime.now(tz=timezone.utc)
            job.pipeline_log = pipeline_log
            await db.commit()

            logger.info("pipeline_completed", job_id=str(job_id), steps=len(step_results))
            return {"status": "completed", "job_id": str(job_id)}

        except PipelineStepError as exc:
            job.status = _JobStatus("failed")
            job.error_message = str(exc)
            job.pipeline_log = {"failed_step": exc.step_name, "error": str(exc)}
            await db.commit()
            logger.error("pipeline_failed", job_id=str(job_id), step=exc.step_name, error=str(exc))
            return {"status": "failed", "step": exc.step_name, "error": str(exc)}

        except Exception as exc:
            job.status = _JobStatus("failed")
            job.error_message = str(exc)
            await db.commit()
            logger.error("pipeline_unexpected_error", job_id=str(job_id), error=str(exc))
            raise

    await engine.dispose()


async def _load_job(db, job_id: UUID):
    from sqlalchemy import select
    # Lazy import to avoid top-level model import issues
    # We import the ORM model from the backend's db package
    # Worker shares the same SQLAlchemy models (same database)
    try:
        from app.db_models import AnalysisJob
        result = await db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))
        return result.scalar_one_or_none()
    except ImportError:
        # Fallback: use raw SQL to update job status
        logger.warning("pipeline_model_import_failed", job_id=str(job_id))
        return None


class _JobStatus:
    """Simple wrapper to allow setting job.status from string in a duck-typed way."""
    def __init__(self, value: str):
        self.value = value

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        if isinstance(other, _JobStatus):
            return self.value == other.value
        return self.value == getattr(other, "value", None)
