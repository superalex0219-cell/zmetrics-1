"""Analysis job management: enqueue Celery tasks."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.db.models.analysis import AnalysisJob, JobStatus


async def enqueue_job(
    db: AsyncSession,
    capture_session_id: uuid.UUID,
    model_version_id: uuid.UUID | None = None,
) -> AnalysisJob:
    """Create an AnalysisJob record and dispatch the Celery pipeline task."""
    job = AnalysisJob(
        capture_session_id=capture_session_id,
        model_version_id=model_version_id,
        status=JobStatus.QUEUED,
    )
    db.add(job)
    await db.flush()  # get job.id before dispatching

    # Dispatch to Celery worker
    task = celery_app.send_task(
        "worker.tasks.pipeline.run_pipeline",
        args=[str(job.id)],
        task_id=str(uuid.uuid4()),
    )
    job.celery_task_id = task.id
    return job
