"""Audit helper for entity edits (EDIT-1).

Writes an append-only AuditLog row with the changed fields only: ``old_value`` holds
the previous values of the fields being changed, ``new_value`` — the new ones.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import AuditLog


def _jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)  # UUID, datetime, Decimal, enum → строка


def apply_update(
    db: AsyncSession,
    *,
    actor_id: uuid.UUID,
    entity: Any,
    entity_type: str,
    changes: dict[str, Any],
    action: str = "entity_updated",
    passport_id: uuid.UUID | None = None,
) -> None:
    """Apply ``changes`` to ``entity`` and write one AuditLog row (changed fields only)."""
    old = {field: _jsonable(getattr(entity, field)) for field in changes}
    for field, value in changes.items():
        setattr(entity, field, value)
    db.add(AuditLog(
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity.id,
        action=action,
        old_value=old,
        new_value={field: _jsonable(value) for field, value in changes.items()},
        passport_id=passport_id,
    ))
