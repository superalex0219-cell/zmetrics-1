from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.blast import Calibration, Device
from app.db.models.user import UserProfile
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.blast import (
    CalibrationCreate,
    CalibrationRead,
    CalibrationUpdate,
    DeviceCreate,
    DeviceRead,
    DeviceUpdate,
)
from app.schemas.common import PaginatedResponse
from app.services.audit import apply_update

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
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Serial number already registered")
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


@router.patch("/{device_id}", response_model=DeviceRead)
async def patch_device(
    device_id: UUID,
    body: DeviceUpdate,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Device:
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    changes = body.model_dump(exclude_unset=True)
    if changes:
        apply_update(
            db, actor_id=current_user.id, entity=device,
            entity_type="device", changes=changes,
        )
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


@router.patch("/{device_id}/calibrations/{calibration_id}", response_model=CalibrationRead)
async def patch_calibration(
    device_id: UUID,
    calibration_id: UUID,
    body: CalibrationUpdate,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Calibration:
    """EDIT-1: только ``is_active`` — матрицы фиксированы, новая калибровка = новая запись."""
    result = await db.execute(
        select(Calibration).where(
            Calibration.id == calibration_id,
            Calibration.device_id == device_id,
        )
    )
    calibration = result.scalar_one_or_none()
    if calibration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calibration not found")
    changes = body.model_dump(exclude_unset=True)
    if changes:
        apply_update(
            db, actor_id=current_user.id, entity=calibration,
            entity_type="calibration", changes=changes,
        )
    return calibration
