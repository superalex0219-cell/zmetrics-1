from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.quarry import Quarry
from app.db.models.user import QuarryUserAccess, Role, UserProfile
from app.db.session import get_db
from app.dependencies import get_current_user

router = APIRouter()


class QuarryAccessEntry(BaseModel):
    quarry_id: UUID
    quarry_name: str
    role_name: str
    role_level: int


@router.get("/access", response_model=list[QuarryAccessEntry])
async def get_my_access(
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[QuarryAccessEntry]:
    """Return the caller's effective role on every quarry they have access to."""
    rows = (await db.execute(
        select(Quarry.id, Quarry.name, Role.name, Role.level)
        .join(QuarryUserAccess, QuarryUserAccess.quarry_id == Quarry.id)
        .join(Role, Role.id == QuarryUserAccess.role_id)
        .where(
            QuarryUserAccess.user_id == current_user.id,
            QuarryUserAccess.revoked_at.is_(None),
            Quarry.deleted_at.is_(None),
        )
        .order_by(Quarry.name)
    )).all()

    return [
        QuarryAccessEntry(
            quarry_id=quarry_id,
            quarry_name=quarry_name,
            role_name=role_name,
            role_level=role_level,
        )
        for quarry_id, quarry_name, role_name, role_level in rows
    ]
