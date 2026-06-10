from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.audit import AuditLog
    from app.db.models.blast import BlastEvent
    from app.db.models.quarry import SiteSection
    from app.db.models.user import UserProfile


class PassportStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    ACTIVE = "active"            # blast authorized
    COMPLETED = "completed"      # blast done, results recorded
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"    # replaced by a new revision


class BlastPassport(Base, TimestampMixin):
    __tablename__ = "blast_passport"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    site_section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("site_section.id"), nullable=False, index=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profile.id"), nullable=False
    )
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profile.id"), nullable=True
    )

    # Versioning: a superseded passport points to its replacement
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blast_passport.id"), nullable=True
    )

    status: Mapped[PassportStatus] = mapped_column(
        SAEnum(PassportStatus, name="passport_status"),
        nullable=False,
        default=PassportStatus.DRAFT,
    )

    # Blast design parameters (БВР fields)
    blast_date_planned: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    explosive_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_explosive_kg: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    number_of_holes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole_diameter_mm: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    hole_depth_m: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    burden_m: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    spacing_m: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    stemming_m: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    # Target P80 from the passport design (mm)
    target_p80_mm: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    site_section: Mapped[SiteSection] = relationship(
        "SiteSection", back_populates="passports"
    )
    created_by: Mapped[UserProfile] = relationship(
        "UserProfile", foreign_keys=[created_by_id]
    )
    approved_by: Mapped[UserProfile | None] = relationship(
        "UserProfile", foreign_keys=[approved_by_id]
    )
    superseded_by: Mapped[BlastPassport | None] = relationship(
        "BlastPassport",
        foreign_keys=[superseded_by_id],
        remote_side="BlastPassport.id",
    )
    blast_event: Mapped[BlastEvent | None] = relationship(
        "BlastEvent", back_populates="passport", uselist=False
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        "AuditLog", back_populates="passport"
    )
