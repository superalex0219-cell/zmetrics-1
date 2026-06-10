from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.passport import BlastPassport
    from app.db.models.user import QuarryUserAccess


class Quarry(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "quarry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)

    site_sections: Mapped[list[SiteSection]] = relationship(
        "SiteSection", back_populates="quarry"
    )
    user_accesses: Mapped[list[QuarryUserAccess]] = relationship(
        "QuarryUserAccess", back_populates="quarry"
    )


class SiteSection(Base, TimestampMixin, SoftDeleteMixin):
    """A named block or section within a quarry where blasting is performed."""

    __tablename__ = "site_section"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    quarry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quarry.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    block_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    quarry: Mapped[Quarry] = relationship("Quarry", back_populates="site_sections")
    passports: Mapped[list[BlastPassport]] = relationship(
        "BlastPassport", back_populates="site_section"
    )
