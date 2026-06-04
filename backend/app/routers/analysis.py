from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analysis import AnalysisJob, AnalysisResult
from app.db.models.user import UserProfile
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.analysis import AnalysisJobCreate, AnalysisJobRead, AnalysisResultRead

router = APIRouter()


@router.post("/{capture_session_id}/jobs", response_model=AnalysisJobRead, status_code=status.HTTP_201_CREATED)
async def enqueue_analysis_job(
    capture_session_id: UUID,
    body: AnalysisJobCreate,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisJob:
    from app.services.analysis import enqueue_job
    job = await enqueue_job(db, capture_session_id, body.model_version_id)
    return job


@router.get("/{capture_session_id}/jobs", response_model=list[AnalysisJobRead])
async def list_jobs(
    capture_session_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AnalysisJob]:
    result = await db.execute(
        select(AnalysisJob).where(AnalysisJob.capture_session_id == capture_session_id)
    )
    return list(result.scalars().all())


@router.get("/{capture_session_id}/jobs/{job_id}", response_model=AnalysisJobRead)
async def get_job(
    capture_session_id: UUID,
    job_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisJob:
    result = await db.execute(
        select(AnalysisJob).where(
            AnalysisJob.id == job_id,
            AnalysisJob.capture_session_id == capture_session_id,
        )
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.get("/{capture_session_id}/jobs/{job_id}/result", response_model=AnalysisResultRead)
async def get_job_result(
    capture_session_id: UUID,
    job_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisResult:
    result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.job_id == job_id)
    )
    analysis_result = result.scalar_one_or_none()
    if analysis_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not available yet or job failed",
        )
    return analysis_result
