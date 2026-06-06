from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel, check_quarry_access
from app.db.models.analysis import AnalysisResult
from app.db.models.user import UserProfile
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.analysis import AnalysisResultRead

router = APIRouter()


async def _quarry_id_for_result(result_id: UUID, db: AsyncSession) -> UUID:
    """Resolve the owning quarry by walking the entity chain up to SiteSection.

    Mirrors reports._quarry_id_for_report: AnalysisResult -> AnalysisJob ->
    CaptureSession -> BlastEvent -> BlastPassport -> SiteSection.quarry_id.
    """
    from app.db.models.analysis import AnalysisJob
    from app.db.models.blast import BlastEvent
    from app.db.models.capture import CaptureSession
    from app.db.models.passport import BlastPassport
    from app.db.models.quarry import SiteSection
    result = await db.execute(
        select(SiteSection.quarry_id)
        .join(BlastPassport, BlastPassport.site_section_id == SiteSection.id)
        .join(BlastEvent, BlastEvent.passport_id == BlastPassport.id)
        .join(CaptureSession, CaptureSession.blast_event_id == BlastEvent.id)
        .join(AnalysisJob, AnalysisJob.capture_session_id == CaptureSession.id)
        .join(AnalysisResult, AnalysisResult.job_id == AnalysisJob.id)
        .where(AnalysisResult.id == result_id)
    )
    quarry_id = result.scalar_one_or_none()
    if quarry_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis result not found"
        )
    return quarry_id


@router.get("/{result_id}", response_model=AnalysisResultRead)
async def get_analysis_result(
    result_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisResult:
    """Fetch a single AnalysisResult by id. USER+ on the owning quarry only."""
    quarry_id = await _quarry_id_for_result(result_id, db)
    await check_quarry_access(db, current_user.id, quarry_id, RoleLevel.USER)

    result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.id == result_id)
    )
    analysis_result = result.scalar_one_or_none()
    if analysis_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis result not found"
        )
    return analysis_result
