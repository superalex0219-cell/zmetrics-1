from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import AuditLog
from app.db.models.user import QuarryUserAccess, Role, UserProfile
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.user import QuarryAccessCreate, QuarryAccessRead, UserProfileRead

router = APIRouter()


async def _require_any_admin(
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    """Check if user is admin on at least one quarry."""
    from app.db.models.user import Role
    result = await db.execute(
        select(QuarryUserAccess)
        .join(Role, Role.id == QuarryUserAccess.role_id)
        .where(
            QuarryUserAccess.user_id == current_user.id,
            QuarryUserAccess.revoked_at.is_(None),
            Role.level >= 4,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


@router.get("/users", response_model=list[UserProfileRead])
async def list_users(
    current_user: UserProfile = Depends(_require_any_admin),
    db: AsyncSession = Depends(get_db),
) -> list[UserProfile]:
    result = await db.execute(select(UserProfile).where(UserProfile.is_active.is_(True)))
    return list(result.scalars().all())


@router.post("/quarries/{quarry_id}/access", response_model=QuarryAccessRead, status_code=status.HTTP_201_CREATED)
async def grant_access(
    quarry_id: UUID,
    body: QuarryAccessCreate,
    current_user: UserProfile = Depends(_require_any_admin),
    db: AsyncSession = Depends(get_db),
) -> QuarryUserAccess:
    role_result = await db.execute(select(Role).where(Role.name == body.role_name))
    role = role_result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown role: {body.role_name}")

    access = QuarryUserAccess(
        user_id=body.user_id,
        quarry_id=quarry_id,
        role_id=role.id,
        granted_by_id=current_user.id,
    )
    db.add(access)
    await db.flush()

    db.add(AuditLog(
        actor_id=current_user.id,
        entity_type="quarry_user_access",
        entity_id=access.id,
        action="role_assigned",
        new_value={"user_id": str(body.user_id), "role": body.role_name, "quarry_id": str(quarry_id)},
    ))
    return access


@router.delete("/quarries/{quarry_id}/access/{access_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_access(
    quarry_id: UUID,
    access_id: UUID,
    current_user: UserProfile = Depends(_require_any_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    from datetime import datetime, timezone
    result = await db.execute(
        select(QuarryUserAccess).where(
            QuarryUserAccess.id == access_id,
            QuarryUserAccess.quarry_id == quarry_id,
        )
    )
    access = result.scalar_one_or_none()
    if access is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access record not found")
    access.revoked_at = datetime.now(tz=timezone.utc)
    db.add(AuditLog(
        actor_id=current_user.id,
        entity_type="quarry_user_access",
        entity_id=access.id,
        action="role_revoked",
        old_value={"quarry_id": str(quarry_id)},
    ))


@router.get("/audit-logs", response_model=list[dict])
async def list_audit_logs(
    entity_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
    current_user: UserProfile = Depends(_require_any_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    query = select(AuditLog).order_by(AuditLog.occurred_at.desc())
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "actor_id": str(log.actor_id) if log.actor_id else None,
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id),
            "action": log.action,
            "occurred_at": log.occurred_at.isoformat(),
            "old_value": log.old_value,
            "new_value": log.new_value,
        }
        for log in logs
    ]
