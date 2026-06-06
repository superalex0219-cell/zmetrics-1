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

    # Derived safety label (product-safety.md): clients must show whether the
    # underlying analysis came from the mock pipeline or a real CV model.
    # NOT stored — assembled via from_report() below. Defaults keep
    # from_attributes mapping happy when read straight off a Report ORM row.
    analysis_method: str = "mock"
    model_version_tag: str | None = None
    confidence_score: float | None = None

    @classmethod
    def from_report(
        cls,
        report: object,
        *,
        confidence_score: object | None = None,
        model_type: str | None = None,
        model_version_tag: str | None = None,
    ) -> "ReportRead":
        """Build a ReportRead, deriving the mock-vs-real safety label.

        SINGLE SOURCE OF TRUTH for the rule — callers pass the values they fetched
        from AnalysisResult/ModelVersion; the mock/real decision lives only here so
        it cannot drift between the single-report and list endpoints.
        SAFETY (product-safety.md): no model_version, or model_type == "mock",
        means the result is synthetic ("mock"); any other model_type is "real".
        Never hardcoded — derived from ModelVersion.model_type.
        """
        analysis_method = "real" if (model_type and model_type != "mock") else "mock"
        return cls.model_validate(report).model_copy(update={
            "analysis_method": analysis_method,
            "model_version_tag": model_version_tag,
            "confidence_score": float(confidence_score) if confidence_score is not None else None,
        })


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
