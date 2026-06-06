from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel, require_quarry_role
from app.db.models.blast import BlastEvent, Calibration, Device
from app.db.models.capture import CaptureSession
from app.db.models.passport import BlastPassport, PassportStatus
from app.db.models.user import UserProfile
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.blast import (
    BlastEventCreate,
    BlastEventRead,
    CaptureSessionCreate,
    CaptureSessionRead,
)
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("/blast-event", response_model=BlastEventRead)
async def get_blast_event(
    quarry_id: UUID,
    passport_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BlastEvent:
    result = await db.execute(
        select(BlastEvent).where(BlastEvent.passport_id == passport_id)
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No blast event for this passport",
        )
    return event


@router.post(
    "/blast-event",
    response_model=BlastEventRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_blast_event(
    quarry_id: UUID,
    passport_id: UUID,
    body: BlastEventCreate,
    current_user: UserProfile = Depends(require_quarry_role(RoleLevel.BLASTER)),
    db: AsyncSession = Depends(get_db),
) -> BlastEvent:
    passport_result = await db.execute(
        select(BlastPassport).where(BlastPassport.id == passport_id)
    )
    passport = passport_result.scalar_one_or_none()
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found")
    if passport.status not in (PassportStatus.APPROVED, PassportStatus.ACTIVE):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot create blast event for passport in status {passport.status.value}",
        )

    existing_result = await db.execute(
        select(BlastEvent).where(BlastEvent.passport_id == passport_id)
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Blast event already exists for this passport",
        )

    event = BlastEvent(
        passport_id=passport_id,
        executed_by_id=current_user.id,
        **body.model_dump(),
    )
    db.add(event)
    await db.flush()
    return event


@router.get("/blast-event/capture-sessions", response_model=PaginatedResponse[CaptureSessionRead])
async def list_capture_sessions(
    quarry_id: UUID,
    passport_id: UUID,
    page: int = 1,
    page_size: int = 20,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[CaptureSessionRead]:
    event_result = await db.execute(
        select(BlastEvent).where(BlastEvent.passport_id == passport_id)
    )
    event = event_result.scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No blast event for this passport",
        )
    base = select(CaptureSession).where(CaptureSession.blast_event_id == event.id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    items = list((await db.execute(
        base.offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/blast-event/capture-sessions",
    response_model=CaptureSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_capture_session(
    quarry_id: UUID,
    passport_id: UUID,
    body: CaptureSessionCreate,
    current_user: UserProfile = Depends(require_quarry_role(RoleLevel.SURVEYOR)),
    db: AsyncSession = Depends(get_db),
) -> CaptureSession:
    event_result = await db.execute(
        select(BlastEvent).where(BlastEvent.passport_id == passport_id)
    )
    event = event_result.scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No blast event for this passport",
        )

    device_result = await db.execute(select(Device).where(Device.id == body.device_id))
    if device_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    cal_result = await db.execute(
        select(Calibration).where(Calibration.id == body.calibration_id)
    )
    if cal_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Calibration not found"
        )

    session = CaptureSession(
        blast_event_id=event.id,
        captured_by_id=current_user.id,
        **body.model_dump(),
    )
    db.add(session)
    await db.flush()
    return session
