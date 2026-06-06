from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.blast import Calibration, Device
from app.db.models.user import UserProfile
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.blast import CalibrationCreate, CalibrationRead, DeviceCreate, DeviceRead
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[DeviceRead])
async def list_devices(
    page: int = 1,
    page_size: int = 20,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[DeviceRead]:
    total = (await db.execute(select(func.count()).select_from(Device))).scalar_one()
    items = list((await db.execute(
        select(Device).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
async def register_device(
    body: DeviceCreate,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Device:
    device = Device(**body.model_dump())
    db.add(device)
    await db.flush()
    return device


@router.get("/{device_id}", response_model=DeviceRead)
async def get_device(
    device_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Device:
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


@router.get("/{device_id}/calibrations", response_model=PaginatedResponse[CalibrationRead])
async def list_calibrations(
    device_id: UUID,
    page: int = 1,
    page_size: int = 20,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[CalibrationRead]:
    base = select(Calibration).where(Calibration.device_id == device_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    items = list((await db.execute(
        base.offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/{device_id}/calibrations",
    response_model=CalibrationRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_calibration(
    device_id: UUID,
    body: CalibrationCreate,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Calibration:
    result = await db.execute(select(Device).where(Device.id == device_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    calibration = Calibration(
        device_id=device_id,
        calibrated_by_id=current_user.id,
        **body.model_dump(),
    )
    db.add(calibration)
    await db.flush()
    return calibration
