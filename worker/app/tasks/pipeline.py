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
    from app.db_models import JobStatus
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
        job.status = JobStatus("running")
        job.started_at = datetime.now(tz=timezone.utc)
        await db.commit()

        # Build S3 client
        s3_client = boto3.client(
            "s3",
            endpoint_url=f"http{'s' if settings.minio_use_ssl else ''}://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
        )

        frame_index = getattr(job, "frame_index", 0) or 0
        ctx = PipelineContext(
            job_id=job_id,
            capture_session_id=job.capture_session_id,
            storage_client=s3_client,
            db_session=db,
            config={"frame_index": frame_index},
            bucket_frames=settings.minio_bucket_frames,
            bucket_artifacts=settings.minio_bucket_artifacts,
        )

        # Determine whether to use real stereo CV steps
        use_real_stereo = settings.enable_real_stereo and await _has_right_frame(
            db, job.capture_session_id, frame_index
        )

        if use_real_stereo:
            from app.pipeline.cv_calibration import CVCalibrationStep
            from app.pipeline.cv_rectification import CVRectificationStep
            from app.pipeline.cv_pointcloud import CVPointCloudStep
            calibration_step = CVCalibrationStep()
            rectification_step = CVRectificationStep()
            if settings.depth_backend == "igev":
                from app.pipeline.cv_depth_igev import IGEVDepthStep
                depth_step = IGEVDepthStep(
                    settings.igev_ckpt_path,
                    valid_iters=settings.igev_valid_iters,
                    max_inference_width=settings.igev_max_inference_width,
                )
            else:
                from app.pipeline.cv_depth import CVStereoDepthStep
                depth_step = CVStereoDepthStep()
            pointcloud_step = CVPointCloudStep()
        else:
            calibration_step = MockCalibrationStep()
            rectification_step = MockRectificationStep()
            depth_step = MockDepthStep()
            pointcloud_step = MockPointCloudStep()

        # SAM3 needs a GPU — behind its own flag, mock segmentation otherwise
        if settings.enable_sam3:
            from app.pipeline.sam3_segmentation import Sam3SegmentationStep
            segmentation_step = Sam3SegmentationStep(
                model_path=settings.sam3_model_path,
                text_prompt=settings.sam3_text_prompt,
                threshold=settings.sam3_confidence_threshold,
            )
        else:
            segmentation_step = MockSegmentationStep()

        # Real particle measurement needs both real depth and real masks;
        # otherwise metric sizes would be derived from synthetic geometry.
        use_real_granulometry = use_real_stereo and settings.enable_sam3
        if use_real_granulometry:
            from app.pipeline.cv_granulometry import CVGranulometryStep
            from app.pipeline.cv_particles import CVParticleVolumeStep
            particles_step = CVParticleVolumeStep()
            granulometry_step = CVGranulometryStep()
        else:
            particles_step = MockParticleVolumeStep()
            granulometry_step = MockGranulometryStep()

        pipeline = Pipeline([
            calibration_step,
            rectification_step,
            depth_step,
            pointcloud_step,
            segmentation_step,
            particles_step,
            granulometry_step,
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

            job.status = JobStatus("completed")
            job.completed_at = datetime.now(tz=timezone.utc)
            job.pipeline_log = pipeline_log

            await _create_report_and_recommendation(
                db,
                job_id,
                job.capture_session_id,
                analysis_method="cv" if use_real_granulometry else "mock",
            )
            await db.commit()

            logger.info("pipeline_completed", job_id=str(job_id), steps=len(step_results))
            return {"status": "completed", "job_id": str(job_id)}

        except PipelineStepError as exc:
            job.status = JobStatus("failed")
            job.error_message = str(exc)
            job.pipeline_log = {"failed_step": exc.step_name, "error": str(exc)}
            await db.commit()
            logger.error("pipeline_failed", job_id=str(job_id), step=exc.step_name, error=str(exc))
            return {"status": "failed", "step": exc.step_name, "error": str(exc)}

        except Exception as exc:
            job.status = JobStatus("failed")
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


async def _has_right_frame(db, capture_session_id: UUID, frame_index: int = 0) -> bool:
    """Check if the job's frame pair has a right_frame artifact."""
    from sqlalchemy import select
    from app.db_models import Artifact, ArtifactType
    frame_filter = Artifact.frame_index == frame_index
    if frame_index == 0:  # legacy uploads have NULL frame_index
        frame_filter = frame_filter | Artifact.frame_index.is_(None)
    result = await db.execute(
        select(Artifact).where(
            Artifact.capture_session_id == capture_session_id,
            Artifact.artifact_type == ArtifactType.RIGHT_FRAME,
            frame_filter,
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _create_report_and_recommendation(
    db,
    job_id: UUID,
    capture_session_id: UUID,
    analysis_method: str = "mock",
) -> None:
    """
    Create Report + Recommendation after successful pipeline.
    SAFETY: Recommendation always created with status=REQUIRES_HUMAN_REVIEW.
    """
    from sqlalchemy import select

    from app.db_models import (
        AnalysisResult,
        BlastEvent,
        BlastPassport,
        CaptureSession,
        Recommendation,
        RecommendationStatus,
        Report,
    )
    from app.config import get_settings
    from app.llm import enhance_recommendation_text
    from app.rules import evaluate_fragmentation

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

    # Resolve BlastPassport to get target_p80_mm for rule evaluation
    blast_event = (await db.execute(
        select(BlastEvent).where(BlastEvent.id == session.blast_event_id)
    )).scalar_one_or_none()

    passport = None
    if blast_event is not None:
        passport = (await db.execute(
            select(BlastPassport).where(BlastPassport.id == blast_event.passport_id)
        )).scalar_one_or_none()

    target_p80_mm = (
        float(passport.target_p80_mm)
        if (passport and passport.target_p80_mm is not None)
        else None
    )

    if ar.p80_mm is None:
        # Nothing was measured (e.g. real CV detected zero particles) — a report
        # or recommendation built on an empty distribution would be misleading.
        logger.warning("pipeline_empty_result_no_report", job_id=str(job_id))
        return

    p10: float | None = float(ar.p10_mm) if ar.p10_mm is not None else None
    p50: float | None = float(ar.p50_mm) if ar.p50_mm is not None else None
    p80 = float(ar.p80_mm)
    conf = float(ar.confidence_score) if ar.confidence_score is not None else 0.0

    # SAFETY: the analysis method must be displayed prominently in the report.
    if analysis_method == "cv":
        title = f"Granulometric Analysis (P80={p80:.0f}mm) — real CV (SAM3 + stereo depth)"
    else:
        title = f"⚠ Mock pipeline — Granulometric Analysis (P80={p80:.0f}mm)"

    report = Report(
        analysis_result_id=ar.id,
        generated_by_id=session.captured_by_id,
        report_type="granulometric",
        title=title,
    )
    db.add(report)
    await db.flush()

    rule_result = evaluate_fragmentation(
        p80_mm=p80,
        fines_percent=float(ar.fines_percent) if ar.fines_percent is not None else 0.0,
        confidence_score=conf,
        target_p80_mm=target_p80_mm,
        p10_mm=p10,
        p50_mm=p50,
    )

    # Optional LLM-enhanced prose. Falls back to the deterministic rule text on
    # any failure / when disabled. Badge + footer are guaranteed by the enhancer.
    final_text = enhance_recommendation_text(
        rule_result=rule_result,
        p10_mm=p10,
        p50_mm=p50,
        p80_mm=p80,
        confidence_score=conf,
        target_p80_mm=target_p80_mm,
        settings=get_settings(),
    )

    # SAFETY: always REQUIRES_HUMAN_REVIEW — never auto-accept.
    # parameter_suggestions stays exactly what the rule engine produced — never from LLM.
    recommendation = Recommendation(
        report_id=report.id,
        generated_by_id=session.captured_by_id,
        status=RecommendationStatus.REQUIRES_HUMAN_REVIEW,
        recommendation_text=final_text,
        parameter_suggestions=rule_result.parameter_suggestions,
    )
    db.add(recommendation)
    await db.flush()

    # Append rule-engine confidence notes without clobbering the original mock note.
    if rule_result.confidence_notes:
        existing = ar.confidence_notes or ""
        ar.confidence_notes = (existing + " | " + rule_result.confidence_notes).lstrip(" | ")

    logger.info(
        "pipeline_report_created",
        job_id=str(job_id),
        report_id=str(report.id),
        p80=p80,
        target_p80_mm=target_p80_mm,
        flags=rule_result.flags,
        confidence=conf,
    )


