from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel, require_quarry_role
from app.db.models.report import Recommendation, RecommendationStatus, Report
from app.db.models.user import UserProfile
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.report import CommentCreate, CommentRead, RecommendationRead, RecommendationReviewRequest, ReportRead

router = APIRouter()


@router.get("/{report_id}", response_model=ReportRead)
async def get_report(
    report_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Report:
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@router.get("/{report_id}/recommendations", response_model=list[RecommendationRead])
async def list_recommendations(
    report_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Recommendation]:
    result = await db.execute(
        select(Recommendation).where(Recommendation.report_id == report_id)
    )
    return list(result.scalars().all())


@router.post("/{report_id}/recommendations/{rec_id}/review", response_model=RecommendationRead)
async def review_recommendation(
    report_id: UUID,
    rec_id: UUID,
    body: RecommendationReviewRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Recommendation:
    result = await db.execute(
        select(Recommendation).where(
            Recommendation.id == rec_id,
            Recommendation.report_id == report_id,
        )
    )
    rec = result.scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")

    if body.status not in (
        RecommendationStatus.REVIEWED,
        RecommendationStatus.ACCEPTED,
        RecommendationStatus.REJECTED,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid review status. Use: reviewed, accepted, or rejected",
        )

    rec.status = body.status
    rec.reviewed_by_id = current_user.id
    rec.reviewed_at = datetime.now(tz=timezone.utc)
    rec.reviewer_notes = body.reviewer_notes

    from app.db.models.audit import AuditLog
    db.add(AuditLog(
        actor_id=current_user.id,
        entity_type="recommendation",
        entity_id=rec.id,
        action="recommendation_reviewed",
        new_value={"status": body.status.value},
    ))
    return rec


@router.post("/{report_id}/recommendations/{rec_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
async def add_comment(
    report_id: UUID,
    rec_id: UUID,
    body: CommentCreate,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommentRead:
    from app.db.models.report import Comment
    comment = Comment(
        recommendation_id=rec_id,
        author_id=current_user.id,
        body=body.body,
    )
    db.add(comment)
    await db.flush()
    return comment
