from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.passport import BlastPassport
    from app.db.models.user import UserProfile


class AuditLog(Base):
    """Append-only audit trail. Records must never be deleted or updated."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profile.id"), nullable=True
    )

    # What entity was changed
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g., "blast_passport", "recommendation", "quarry_user_access"
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    action: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g., "status_changed", "role_assigned", "revision_created", "recommendation_reviewed"

    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Convenience FK to passport for quick filtering of passport-related events
    passport_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blast_passport.id"), nullable=True, index=True
    )
    # Free-form notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    actor: Mapped[UserProfile | None] = relationship(
        "UserProfile", back_populates="audit_logs", foreign_keys=[actor_id]
    )
    passport: Mapped[BlastPassport | None] = relationship(
        "BlastPassport", back_populates="audit_logs", foreign_keys=[passport_id]
    )
