"""Role-based access control. Roles are per-quarry (QuarryUserAccess)."""

from __future__ import annotations

import enum
import uuid
from typing import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db


class RoleLevel(int, enum.Enum):
    USER = 1
    SURVEYOR = 2
    BLASTER = 3
    ADMIN = 4


KEYCLOAK_ROLE_MAP = {
    "zmetrics-user": RoleLevel.USER,
    "zmetrics-surveyor": RoleLevel.SURVEYOR,
    "zmetrics-blaster": RoleLevel.BLASTER,
    "zmetrics-admin": RoleLevel.ADMIN,
}


def require_quarry_role(minimum_level: RoleLevel) -> Callable:
    """
    Returns a FastAPI dependency that enforces the caller has at least `minimum_level`
    for the `quarry_id` path parameter.

    Usage:
        @router.post("/{quarry_id}/passports")
        async def create_passport(
            ...,
            _: UserProfile = Depends(require_quarry_role(RoleLevel.BLASTER)),
        ):
    """
    from app.dependencies import get_current_user
    from app.db.models.user import QuarryUserAccess, UserProfile

    async def check_role(
        quarry_id: uuid.UUID,
        current_user: UserProfile = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> UserProfile:
        result = await db.execute(
            select(QuarryUserAccess)
            .where(
                QuarryUserAccess.user_id == current_user.id,
                QuarryUserAccess.quarry_id == quarry_id,
                QuarryUserAccess.revoked_at.is_(None),
            )
        )
        access = result.scalar_one_or_none()
        if access is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No access to this quarry",
            )

        # Load the role level
        from app.db.models.user import Role
        role_result = await db.execute(
            select(Role).where(Role.id == access.role_id)
        )
        role = role_result.scalar_one_or_none()
        if role is None or role.level < minimum_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role level {minimum_level.name} or higher",
            )
        return current_user

    return check_role


def _build_require_any_admin():
    """Dependency: caller must be ADMIN (level 4) on at least one quarry."""
    from app.dependencies import get_current_user
    from app.db.models.user import QuarryUserAccess, Role, UserProfile

    async def _dep(
        current_user: UserProfile = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> UserProfile:
        result = await db.execute(
            select(QuarryUserAccess.id)
            .join(Role, Role.id == QuarryUserAccess.role_id)
            .where(
                QuarryUserAccess.user_id == current_user.id,
                QuarryUserAccess.revoked_at.is_(None),
                Role.level >= RoleLevel.ADMIN,
            )
            .limit(1)  # admin on several quarries is normal — any one row suffices
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        return current_user

    return _dep


require_any_admin = _build_require_any_admin()


async def check_quarry_access(
    db: AsyncSession,
    user_id: "uuid.UUID",
    quarry_id: "uuid.UUID",
    minimum_level: RoleLevel,
) -> None:
    """Raise HTTP 403 if user lacks minimum_level on quarry_id."""
    from app.db.models.user import QuarryUserAccess, Role
    result = await db.execute(
        select(Role.level)
        .join(QuarryUserAccess, QuarryUserAccess.role_id == Role.id)
        .where(
            QuarryUserAccess.user_id == user_id,
            QuarryUserAccess.quarry_id == quarry_id,
            QuarryUserAccess.revoked_at.is_(None),
        )
    )
    level = result.scalar_one_or_none()
    if level is None or level < minimum_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires role level {minimum_level.name} or higher",
        )
