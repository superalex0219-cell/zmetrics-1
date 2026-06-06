from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel, require_any_admin, require_quarry_role
from app.db.models.quarry import Quarry, SiteSection
from app.db.models.user import UserProfile
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.common import PaginatedResponse
from app.schemas.quarry import QuarryCreate, QuarryRead, QuarryUpdate, SiteSectionCreate, SiteSectionRead
from app.schemas.report import ReportRead

router = APIRouter()


@router.get("", response_model=PaginatedResponse[QuarryRead])
async def list_quarries(
    page: int = 1,
    page_size: int = 20,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[QuarryRead]:
    from app.db.models.user import QuarryUserAccess
    base = (
        select(Quarry)
        .join(QuarryUserAccess, QuarryUserAccess.quarry_id == Quarry.id)
        .where(
            QuarryUserAccess.user_id == current_user.id,
            QuarryUserAccess.revoked_at.is_(None),
            Quarry.deleted_at.is_(None),
        )
    )
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    items = list((await db.execute(
        base.offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=QuarryRead, status_code=status.HTTP_201_CREATED)
async def create_quarry(
    body: QuarryCreate,
    current_user: UserProfile = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
) -> Quarry:
    quarry = Quarry(**body.model_dump())
    db.add(quarry)
    await db.flush()
    return quarry


@router.get("/{quarry_id}", response_model=QuarryRead)
async def get_quarry(
    quarry_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Quarry:
    result = await db.execute(
        select(Quarry).where(Quarry.id == quarry_id, Quarry.deleted_at.is_(None))
    )
    quarry = result.scalar_one_or_none()
    if quarry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quarry not found")
    return quarry


@router.put("/{quarry_id}", response_model=QuarryRead)
async def update_quarry(
    quarry_id: UUID,
    body: QuarryUpdate,
    current_user: UserProfile = Depends(require_quarry_role(RoleLevel.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> Quarry:
    result = await db.execute(
        select(Quarry).where(Quarry.id == quarry_id, Quarry.deleted_at.is_(None))
    )
    quarry = result.scalar_one_or_none()
    if quarry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quarry not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(quarry, field, value)
    return quarry


@router.get("/{quarry_id}/sections", response_model=PaginatedResponse[SiteSectionRead])
async def list_site_sections(
    quarry_id: UUID,
    page: int = 1,
    page_size: int = 20,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SiteSectionRead]:
    base = select(SiteSection).where(
        SiteSection.quarry_id == quarry_id,
        SiteSection.deleted_at.is_(None),
    )
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    items = list((await db.execute(
        base.offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{quarry_id}/reports", response_model=PaginatedResponse[ReportRead])
async def list_quarry_reports(
    quarry_id: UUID,
    page: int = 1,
    page_size: int = 20,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ReportRead]:
    from app.db.models.analysis import AnalysisJob, AnalysisResult
    from app.db.models.blast import BlastEvent
    from app.db.models.capture import CaptureSession
    from app.db.models.passport import BlastPassport
    from app.db.models.report import Report
    base = (
        select(Report)
        .join(AnalysisResult, AnalysisResult.id == Report.analysis_result_id)
        .join(AnalysisJob, AnalysisJob.id == AnalysisResult.job_id)
        .join(CaptureSession, CaptureSession.id == AnalysisJob.capture_session_id)
        .join(BlastEvent, BlastEvent.id == CaptureSession.blast_event_id)
        .join(BlastPassport, BlastPassport.id == BlastEvent.passport_id)
        .join(SiteSection, SiteSection.id == BlastPassport.site_section_id)
        .where(SiteSection.quarry_id == quarry_id)
        .order_by(Report.created_at.desc())
    )
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    items = list((await db.execute(
        base.offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/{quarry_id}/sections", response_model=SiteSectionRead, status_code=status.HTTP_201_CREATED)
async def create_site_section(
    quarry_id: UUID,
    body: SiteSectionCreate,
    current_user: UserProfile = Depends(require_quarry_role(RoleLevel.BLASTER)),
    db: AsyncSession = Depends(get_db),
) -> SiteSection:
    section = SiteSection(quarry_id=quarry_id, name=body.name, block_number=body.block_number, description=body.description)
    db.add(section)
    await db.flush()
    return section
