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

            await _create_report_and_recommendation(db, job_id, job.capture_session_id)
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


async def _create_report_and_recommendation(
    db,
    job_id: UUID,
    capture_session_id: UUID,
) -> None:
    """
    Create Report + Recommendation after successful pipeline.
    SAFETY: Recommendation always created with status=REQUIRES_HUMAN_REVIEW.
    """
    from sqlalchemy import select

    from app.db_models import (
        AnalysisResult,
        CaptureSession,
        Recommendation,
        RecommendationStatus,
        Report,
    )

    # Get AnalysisResult created by granulometry step
    ar = (await db.execute(
        select(AnalysisResult).where(AnalysisResult.job_id == job_id)
    )).scalar_one_or_none()
    if ar is None:
        logger.warning("pipeline_no_analysis_result", job_id=str(job_id))
        return

    # Get who captured this session (required for Report.generated_by_id)
    session = (await db.execute(
        select(CaptureSession).where(CaptureSession.id == capture_session_id)
    )).scalar_one_or_none()
    if session is None:
        logger.warning("pipeline_no_capture_session", job_id=str(job_id))
        return

    p10 = float(ar.p10_mm) if ar.p10_mm is not None else 0.0
    p50 = float(ar.p50_mm) if ar.p50_mm is not None else 0.0
    p80 = float(ar.p80_mm) if ar.p80_mm is not None else 0.0
    conf = float(ar.confidence_score) if ar.confidence_score is not None else 0.0

    report = Report(
        analysis_result_id=ar.id,
        generated_by_id=session.captured_by_id,
        report_type="granulometric",
        title=f"⚠ Mock pipeline — Granulometric Analysis (P80={p80:.0f}mm)",
    )
    db.add(report)
    await db.flush()

    rec_text = (
        f"⚠ Mock pipeline — results are synthetic. "
        f"P10={p10:.0f}mm, P50={p50:.0f}mm, P80={p80:.0f}mm. "
        f"Confidence={conf:.2f}. "
    )
    if conf < 0.5:
        rec_text += "Low confidence — manual re-capture strongly recommended. "
    rec_text += "Review fragmentation metrics and compare against passport target before any design changes."

    # SAFETY: always REQUIRES_HUMAN_REVIEW — never auto-accept.
    recommendation = Recommendation(
        report_id=report.id,
        generated_by_id=session.captured_by_id,
        status=RecommendationStatus.REQUIRES_HUMAN_REVIEW,
        recommendation_text=rec_text,
        parameter_suggestions=None,
    )
    db.add(recommendation)
    await db.flush()

    logger.info(
        "pipeline_report_created",
        job_id=str(job_id),
        report_id=str(report.id),
        p80=p80,
        confidence=conf,
    )


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
