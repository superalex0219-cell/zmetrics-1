from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel, require_quarry_role
from app.db.models.audit import AuditLog
from app.db.models.quarry import Quarry, SiteSection
from app.db.models.user import QuarryUserAccess, Role, UserProfile
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.common import PaginatedResponse
from app.schemas.quarry import (
    QuarryCreate,
    QuarryRead,
    QuarryUpdate,
    SiteSectionCreate,
    SiteSectionRead,
    SiteSectionUpdate,
)
from app.services.audit import apply_update
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
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Quarry:
    active_quarries = (
        await db.execute(
            select(func.count()).select_from(Quarry).where(Quarry.deleted_at.is_(None))
        )
    ).scalar_one()
    admin_access = (
        await db.execute(
            select(QuarryUserAccess.id)
            .join(Role, Role.id == QuarryUserAccess.role_id)
            .where(
                QuarryUserAccess.user_id == current_user.id,
                QuarryUserAccess.revoked_at.is_(None),
                Role.level >= RoleLevel.ADMIN.value,
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    if active_quarries > 0 and admin_access is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    quarry = Quarry(**body.model_dump())
    db.add(quarry)
    await db.flush()

    admin_role = (await db.execute(select(Role).where(Role.name == "admin"))).scalar_one_or_none()
    if admin_role is None:
        admin_role = Role(name="admin", level=RoleLevel.ADMIN.value)
        db.add(admin_role)
        await db.flush()

    access = QuarryUserAccess(
        user_id=current_user.id,
        quarry_id=quarry.id,
        role_id=admin_role.id,
        granted_by_id=current_user.id,
    )
    db.add(access)
    await db.flush()

    db.add(
        AuditLog(
            actor_id=current_user.id,
            entity_type="quarry",
            entity_id=quarry.id,
            action="quarry_created",
            new_value=body.model_dump(),
        )
    )
    db.add(
        AuditLog(
            actor_id=current_user.id,
            entity_type="quarry_user_access",
            entity_id=access.id,
            action="role_assigned",
            new_value={"role": "admin", "quarry_id": str(quarry.id)},
        )
    )
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


async def _update_quarry(
    quarry_id: UUID,
    body: QuarryUpdate,
    current_user: UserProfile,
    db: AsyncSession,
) -> Quarry:
    result = await db.execute(
        select(Quarry).where(Quarry.id == quarry_id, Quarry.deleted_at.is_(None))
    )
    quarry = result.scalar_one_or_none()
    if quarry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quarry not found")
    changes = body.model_dump(exclude_unset=True)
    if changes:
        apply_update(
            db, actor_id=current_user.id, entity=quarry,
            entity_type="quarry", changes=changes,
        )
    return quarry


@router.put("/{quarry_id}", response_model=QuarryRead)
async def update_quarry(
    quarry_id: UUID,
    body: QuarryUpdate,
    current_user: UserProfile = Depends(require_quarry_role(RoleLevel.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> Quarry:
    return await _update_quarry(quarry_id, body, current_user, db)


@router.patch("/{quarry_id}", response_model=QuarryRead)
async def patch_quarry(
    quarry_id: UUID,
    body: QuarryUpdate,
    current_user: UserProfile = Depends(require_quarry_role(RoleLevel.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> Quarry:
    return await _update_quarry(quarry_id, body, current_user, db)


@router.patch("/{quarry_id}/sections/{section_id}", response_model=SiteSectionRead)
async def patch_site_section(
    quarry_id: UUID,
    section_id: UUID,
    body: SiteSectionUpdate,
    current_user: UserProfile = Depends(require_quarry_role(RoleLevel.BLASTER)),
    db: AsyncSession = Depends(get_db),
) -> SiteSection:
    result = await db.execute(
        select(SiteSection).where(
            SiteSection.id == section_id,
            SiteSection.quarry_id == quarry_id,
            SiteSection.deleted_at.is_(None),
        )
    )
    section = result.scalar_one_or_none()
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    changes = body.model_dump(exclude_unset=True)
    if changes:
        apply_update(
            db, actor_id=current_user.id, entity=section,
            entity_type="site_section", changes=changes,
        )
    return section


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
    from app.db.models.analysis import AnalysisJob, AnalysisResult, ModelVersion
    from app.db.models.blast import BlastEvent
    from app.db.models.capture import CaptureSession
    from app.db.models.passport import BlastPassport
    from app.db.models.report import Report
    # Single query: pull each report alongside the safety-label inputs
    # (confidence_score, model_type, version_tag) so there is no per-row N+1.
    base = (
        select(
            Report,
            AnalysisResult.confidence_score,
            ModelVersion.model_type,
            ModelVersion.version_tag,
        )
        .join(AnalysisResult, AnalysisResult.id == Report.analysis_result_id)
        .join(AnalysisJob, AnalysisJob.id == AnalysisResult.job_id)
        .outerjoin(ModelVersion, ModelVersion.id == AnalysisJob.model_version_id)
        .join(CaptureSession, CaptureSession.id == AnalysisJob.capture_session_id)
        .join(BlastEvent, BlastEvent.id == CaptureSession.blast_event_id)
        .join(BlastPassport, BlastPassport.id == BlastEvent.passport_id)
        .join(SiteSection, SiteSection.id == BlastPassport.site_section_id)
        .where(SiteSection.quarry_id == quarry_id)
        .order_by(Report.created_at.desc())
    )
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (await db.execute(
        base.offset((page - 1) * page_size).limit(page_size)
    )).all()
    # Derive the mock-vs-real label via the shared ReportRead.from_report rule so it can't drift.
    items = [
        ReportRead.from_report(
            report,
            confidence_score=confidence_score,
            model_type=model_type,
            model_version_tag=version_tag,
        )
        for report, confidence_score, model_type, version_tag in rows
    ]
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
