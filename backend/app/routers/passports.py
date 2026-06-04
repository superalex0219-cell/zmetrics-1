from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel, require_quarry_role
from app.db.models.passport import BlastPassport, PassportStatus
from app.db.models.user import UserProfile
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.passport import BlastPassportCreate, BlastPassportRead, BlastPassportUpdate

router = APIRouter()


@router.get("", response_model=list[BlastPassportRead])
async def list_passports(
    quarry_id: UUID,
    section_id: UUID | None = None,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BlastPassport]:
    from app.db.models.quarry import SiteSection
    query = (
        select(BlastPassport)
        .join(SiteSection, SiteSection.id == BlastPassport.site_section_id)
        .where(
            SiteSection.quarry_id == quarry_id,
            BlastPassport.status != PassportStatus.SUPERSEDED,
        )
    )
    if section_id:
        query = query.where(BlastPassport.site_section_id == section_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=BlastPassportRead, status_code=status.HTTP_201_CREATED)
async def create_passport(
    quarry_id: UUID,
    body: BlastPassportCreate,
    current_user: UserProfile = Depends(require_quarry_role(RoleLevel.BLASTER)),
    db: AsyncSession = Depends(get_db),
) -> BlastPassport:
    passport = BlastPassport(
        **body.model_dump(),
        created_by_id=current_user.id,
    )
    db.add(passport)
    await db.flush()
    return passport


@router.get("/{passport_id}", response_model=BlastPassportRead)
async def get_passport(
    quarry_id: UUID,
    passport_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BlastPassport:
    passport = await _get_passport_or_404(passport_id, db)
    return passport


@router.put("/{passport_id}", response_model=BlastPassportRead)
async def update_passport(
    quarry_id: UUID,
    passport_id: UUID,
    body: BlastPassportUpdate,
    current_user: UserProfile = Depends(require_quarry_role(RoleLevel.BLASTER)),
    db: AsyncSession = Depends(get_db),
) -> BlastPassport:
    passport = await _get_passport_or_404(passport_id, db)
    if passport.status != PassportStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only DRAFT passports can be updated",
        )
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(passport, field, value)
    return passport


@router.post("/{passport_id}/submit", response_model=BlastPassportRead)
async def submit_passport(
    quarry_id: UUID,
    passport_id: UUID,
    current_user: UserProfile = Depends(require_quarry_role(RoleLevel.BLASTER)),
    db: AsyncSession = Depends(get_db),
) -> BlastPassport:
    passport = await _get_passport_or_404(passport_id, db)
    _assert_status(passport, PassportStatus.DRAFT, "submit")
    passport.status = PassportStatus.SUBMITTED
    await _write_audit(db, current_user.id, passport, "status_changed", "DRAFT", "SUBMITTED")
    return passport


@router.post("/{passport_id}/approve", response_model=BlastPassportRead)
async def approve_passport(
    quarry_id: UUID,
    passport_id: UUID,
    current_user: UserProfile = Depends(require_quarry_role(RoleLevel.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> BlastPassport:
    passport = await _get_passport_or_404(passport_id, db)
    _assert_status(passport, PassportStatus.SUBMITTED, "approve")
    passport.status = PassportStatus.APPROVED
    passport.approved_by_id = current_user.id
    await _write_audit(db, current_user.id, passport, "status_changed", "SUBMITTED", "APPROVED")
    return passport


@router.post("/{passport_id}/revise", response_model=BlastPassportRead, status_code=status.HTTP_201_CREATED)
async def revise_passport(
    quarry_id: UUID,
    passport_id: UUID,
    body: BlastPassportUpdate,
    current_user: UserProfile = Depends(require_quarry_role(RoleLevel.BLASTER)),
    db: AsyncSession = Depends(get_db),
) -> BlastPassport:
    from app.services.passport import create_revision
    old_passport = await _get_passport_or_404(passport_id, db)
    new_passport = await create_revision(db, old_passport, body.model_dump(exclude_unset=True), current_user.id)
    return new_passport


async def _get_passport_or_404(passport_id: UUID, db: AsyncSession) -> BlastPassport:
    result = await db.execute(select(BlastPassport).where(BlastPassport.id == passport_id))
    passport = result.scalar_one_or_none()
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found")
    return passport


def _assert_status(passport: BlastPassport, expected: PassportStatus, action: str) -> None:
    if passport.status != expected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot {action} passport in status {passport.status.value}",
        )


async def _write_audit(
    db: AsyncSession,
    actor_id: UUID,
    passport: BlastPassport,
    action: str,
    old_val: str,
    new_val: str,
) -> None:
    from app.db.models.audit import AuditLog
    log = AuditLog(
        actor_id=actor_id,
        entity_type="blast_passport",
        entity_id=passport.id,
        action=action,
        old_value={"status": old_val},
        new_value={"status": new_val},
        passport_id=passport.id,
    )
    db.add(log)
