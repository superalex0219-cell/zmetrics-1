from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.audit import AuditLog
    from app.db.models.quarry import Quarry


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profile"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    keycloak_sub: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    quarry_accesses: Mapped[list[QuarryUserAccess]] = relationship(
        "QuarryUserAccess",
        back_populates="user",
        foreign_keys="QuarryUserAccess.user_id",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        "AuditLog", back_populates="actor", foreign_keys="AuditLog.actor_id"
    )


class Role(Base):
    __tablename__ = "role"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # Values: "user", "surveyor", "blaster", "admin"
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    # Levels: user=1, surveyor=2, blaster=3, admin=4

    quarry_accesses: Mapped[list[QuarryUserAccess]] = relationship(
        "QuarryUserAccess", back_populates="role"
    )


class QuarryUserAccess(Base, TimestampMixin):
    """Per-quarry role assignment. One user may have different roles on different quarries."""

    __tablename__ = "quarry_user_access"
    __table_args__ = (
        # Partial index: only one active (non-revoked) role per user per quarry.
        # Full UniqueConstraint would block re-granting after revocation.
        # sqlite_where keeps the test database (aiosqlite) semantics identical.
        Index(
            "uq_quarry_user_active",
            "user_id", "quarry_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
            sqlite_where=text("revoked_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profile.id"), nullable=False, index=True
    )
    quarry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quarry.id"), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("role.id"), nullable=False
    )
    granted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profile.id"), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[UserProfile] = relationship(
        "UserProfile", back_populates="quarry_accesses", foreign_keys=[user_id]
    )
    quarry: Mapped[Quarry] = relationship("Quarry", back_populates="user_accesses")
    role: Mapped[Role] = relationship("Role", back_populates="quarry_accesses")
    granted_by: Mapped[UserProfile | None] = relationship(
        "UserProfile", foreign_keys=[granted_by_id]
    )
