from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.models.report import RecommendationStatus


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_result_id: UUID
    generated_by_id: UUID
    report_type: str
    title: str
    artifact_id: UUID | None
    created_at: datetime


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_id: UUID
    status: RecommendationStatus
    recommendation_text: str
    parameter_suggestions: dict | None
    reviewed_at: datetime | None
    reviewer_notes: str | None
    created_at: datetime


class RecommendationReviewRequest(BaseModel):
    status: RecommendationStatus
    reviewer_notes: str | None = None


class CommentCreate(BaseModel):
    body: str


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recommendation_id: UUID
    author_id: UUID
    body: str
    created_at: datetime
