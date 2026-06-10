from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.analysis import AnalysisResult
    from app.db.models.user import UserProfile


class RecommendationStatus(str, enum.Enum):
    # SAFETY: Recommendations MUST always start as one of these two values.
    # Never create a recommendation with status=accepted without explicit human review.
    REQUIRES_HUMAN_REVIEW = "requires_human_review"
    DRAFT = "draft"
    REVIEWED = "reviewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Report(Base, TimestampMixin):
    __tablename__ = "report"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_result.id"), nullable=False, unique=True
    )
    generated_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profile.id"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="granulometric"
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    # Optional: link to PDF/HTML report file artifact in MinIO
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("artifact.id"), nullable=True
    )

    analysis_result: Mapped[AnalysisResult] = relationship(
        "AnalysisResult", back_populates="report"
    )
    generated_by: Mapped[UserProfile] = relationship(
        "UserProfile", foreign_keys=[generated_by_id]
    )
    recommendations: Mapped[list[Recommendation]] = relationship(
        "Recommendation", back_populates="report"
    )


class Recommendation(Base, TimestampMixin):
    """AI-generated BVR recommendation. Always starts as requires_human_review."""

    __tablename__ = "recommendation"

    def __init__(self, **kw: Any) -> None:
        kw.setdefault("status", RecommendationStatus.REQUIRES_HUMAN_REVIEW)
        super().__init__(**kw)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report.id"), nullable=False, index=True
    )
    generated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profile.id"), nullable=True
    )
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profile.id"), nullable=True
    )

    # SAFETY: default is REQUIRES_HUMAN_REVIEW — never auto-approve.
    status: Mapped[RecommendationStatus] = mapped_column(
        SAEnum(RecommendationStatus, name="recommendation_status"),
        nullable=False,
        default=RecommendationStatus.REQUIRES_HUMAN_REVIEW,
    )

    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Suggested parameter adjustments — for human review only, NEVER auto-applied.
    # {"burden_m": 3.2, "spacing_m": 3.8, "rationale": "P80 exceeded target by 15%"}
    parameter_suggestions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    report: Mapped[Report] = relationship("Report", back_populates="recommendations")
    comments: Mapped[list[Comment]] = relationship("Comment", back_populates="recommendation")


class Comment(Base, TimestampMixin):
    __tablename__ = "comment"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recommendation.id"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profile.id"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)

    recommendation: Mapped[Recommendation] = relationship(
        "Recommendation", back_populates="comments"
    )
    author: Mapped[UserProfile] = relationship("UserProfile", foreign_keys=[author_id])
