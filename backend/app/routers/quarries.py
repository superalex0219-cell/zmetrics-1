from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel, require_quarry_role
from app.db.models.quarry import Quarry, SiteSection
from app.db.models.user import UserProfile
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.quarry import QuarryCreate, QuarryRead, QuarryUpdate, SiteSectionCreate, SiteSectionRead

router = APIRouter()


@router.get("", response_model=list[QuarryRead])
async def list_quarries(
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Quarry]:
    from app.db.models.user import QuarryUserAccess
    result = await db.execute(
        select(Quarry)
        .join(QuarryUserAccess, QuarryUserAccess.quarry_id == Quarry.id)
        .where(
            QuarryUserAccess.user_id == current_user.id,
            QuarryUserAccess.revoked_at.is_(None),
            Quarry.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


@router.post("", response_model=QuarryRead, status_code=status.HTTP_201_CREATED)
async def create_quarry(
    body: QuarryCreate,
    current_user: UserProfile = Depends(get_current_user),
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


@router.get("/{quarry_id}/sections", response_model=list[SiteSectionRead])
async def list_site_sections(
    quarry_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SiteSection]:
    result = await db.execute(
        select(SiteSection).where(
            SiteSection.quarry_id == quarry_id,
            SiteSection.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())


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
