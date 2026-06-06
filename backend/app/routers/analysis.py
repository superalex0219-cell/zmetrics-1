from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel, check_quarry_access
from app.db.models.analysis import AnalysisJob, AnalysisResult
from app.db.models.user import UserProfile
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.analysis import AnalysisJobCreate, AnalysisJobRead, AnalysisResultRead
from app.schemas.common import PaginatedResponse

router = APIRouter()


async def _quarry_id_for_session(session_id: UUID, db: AsyncSession) -> UUID:
    from app.db.models.blast import BlastEvent
    from app.db.models.capture import CaptureSession
    from app.db.models.passport import BlastPassport
    from app.db.models.quarry import SiteSection
    result = await db.execute(
        select(SiteSection.quarry_id)
        .join(BlastPassport, BlastPassport.site_section_id == SiteSection.id)
        .join(BlastEvent, BlastEvent.passport_id == BlastPassport.id)
        .join(CaptureSession, CaptureSession.blast_event_id == BlastEvent.id)
        .where(CaptureSession.id == session_id)
    )
    quarry_id = result.scalar_one_or_none()
    if quarry_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capture session not found")
    return quarry_id


@router.post("/{capture_session_id}/jobs", response_model=AnalysisJobRead, status_code=status.HTTP_201_CREATED)
async def enqueue_analysis_job(
    capture_session_id: UUID,
    body: AnalysisJobCreate,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisJob:
    quarry_id = await _quarry_id_for_session(capture_session_id, db)
    await check_quarry_access(db, current_user.id, quarry_id, RoleLevel.SURVEYOR)
    from app.services.analysis import enqueue_job
    job = await enqueue_job(db, capture_session_id, body.model_version_id)
    return job


@router.get("/{capture_session_id}/jobs", response_model=PaginatedResponse[AnalysisJobRead])
async def list_jobs(
    capture_session_id: UUID,
    page: int = 1,
    page_size: int = 20,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AnalysisJobRead]:
    quarry_id = await _quarry_id_for_session(capture_session_id, db)
    await check_quarry_access(db, current_user.id, quarry_id, RoleLevel.USER)

    base = select(AnalysisJob).where(AnalysisJob.capture_session_id == capture_session_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    items = list((await db.execute(
        base.offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{capture_session_id}/jobs/{job_id}", response_model=AnalysisJobRead)
async def get_job(
    capture_session_id: UUID,
    job_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisJob:
    quarry_id = await _quarry_id_for_session(capture_session_id, db)
    await check_quarry_access(db, current_user.id, quarry_id, RoleLevel.USER)

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
    quarry_id = await _quarry_id_for_session(capture_session_id, db)
    await check_quarry_access(db, current_user.id, quarry_id, RoleLevel.USER)

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
