from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel, check_quarry_access
from app.db.models.report import Recommendation, RecommendationStatus, Report
from app.db.models.user import UserProfile
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.common import PaginatedResponse
from app.schemas.report import CommentCreate, CommentRead, RecommendationRead, RecommendationReviewRequest, ReportRead

router = APIRouter()


async def _quarry_id_for_report(report_id: UUID, db: AsyncSession) -> UUID:
    from app.db.models.analysis import AnalysisJob, AnalysisResult
    from app.db.models.blast import BlastEvent
    from app.db.models.capture import CaptureSession
    from app.db.models.passport import BlastPassport
    from app.db.models.quarry import SiteSection
    result = await db.execute(
        select(SiteSection.quarry_id)
        .join(BlastPassport, BlastPassport.site_section_id == SiteSection.id)
        .join(BlastEvent, BlastEvent.passport_id == BlastPassport.id)
        .join(CaptureSession, CaptureSession.blast_event_id == BlastEvent.id)
        .join(AnalysisJob, AnalysisJob.capture_session_id == CaptureSession.id)
        .join(AnalysisResult, AnalysisResult.job_id == AnalysisJob.id)
        .join(Report, Report.analysis_result_id == AnalysisResult.id)
        .where(Report.id == report_id)
    )
    quarry_id = result.scalar_one_or_none()
    if quarry_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return quarry_id


async def _report_read(report: Report, db: AsyncSession) -> ReportRead:
    """Fetch the safety-label inputs for one report and assemble its ReportRead.

    The mock-vs-real decision itself lives in ReportRead.from_report so it stays
    a single source of truth shared with the quarry-reports list endpoint.
    """
    from app.db.models.analysis import AnalysisJob, AnalysisResult, ModelVersion
    row = (await db.execute(
        select(
            AnalysisResult.confidence_score,
            ModelVersion.model_type,
            ModelVersion.version_tag,
        )
        .select_from(AnalysisResult)
        .join(AnalysisJob, AnalysisJob.id == AnalysisResult.job_id)
        .outerjoin(ModelVersion, ModelVersion.id == AnalysisJob.model_version_id)
        .where(AnalysisResult.id == report.analysis_result_id)
    )).first()

    confidence_score = model_type = version_tag = None
    if row is not None:
        confidence_score, model_type, version_tag = row

    return ReportRead.from_report(
        report,
        confidence_score=confidence_score,
        model_type=model_type,
        model_version_tag=version_tag,
    )


@router.get("/{report_id}", response_model=ReportRead)
async def get_report(
    report_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportRead:
    quarry_id = await _quarry_id_for_report(report_id, db)
    await check_quarry_access(db, current_user.id, quarry_id, RoleLevel.USER)
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return await _report_read(report, db)


@router.get("/{report_id}/export")
async def export_report(
    report_id: UUID,
    format: str = "json",
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export the report as JSON / CSV / XLSX / DOCX / PDF (REPORT-X).

    The rendered file is also persisted to MinIO (``reports/{id}/``, STORE-1)
    so report files live next to the rest of the analysis artifacts.
    """
    from app.services.report_export import (
        EXPORT_FORMATS,
        MEDIA_TYPES,
        collect_report_data,
        collect_report_images,
        render,
    )
    from app.services.storage import get_storage_service

    fmt = format.lower()
    if fmt not in EXPORT_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format {format!r}; use one of {', '.join(EXPORT_FORMATS)}",
        )

    quarry_id = await _quarry_id_for_report(report_id, db)
    await check_quarry_access(db, current_user.id, quarry_id, RoleLevel.BLASTER)

    data = await collect_report_data(db, report_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    storage = get_storage_service()
    images: dict[str, bytes] = {}
    if fmt in ("docx", "pdf"):
        images = await collect_report_images(db, storage, data)

    content = render(fmt, data, images)

    # STORE-1: persist the rendered report file to MinIO (best-effort)
    try:
        import io as _io
        storage.upload_file(
            "zmetrics-artifacts",
            f"reports/{report_id}/report.{fmt}",
            _io.BytesIO(content),
            content_type=MEDIA_TYPES[fmt],
        )
    except Exception:
        pass  # выгрузка пользователю важнее кэша в MinIO

    filename = f"report_{report_id}_{datetime.now(tz=timezone.utc).strftime('%Y%m%d')}.{fmt}"
    return Response(
        content=content,
        media_type=MEDIA_TYPES[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{report_id}/recommendations", response_model=PaginatedResponse[RecommendationRead])
async def list_recommendations(
    report_id: UUID,
    page: int = 1,
    page_size: int = 20,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[RecommendationRead]:
    quarry_id = await _quarry_id_for_report(report_id, db)
    await check_quarry_access(db, current_user.id, quarry_id, RoleLevel.USER)

    base = select(Recommendation).where(Recommendation.report_id == report_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    items = list((await db.execute(
        base.offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/{report_id}/recommendations/{rec_id}/review", response_model=RecommendationRead)
async def review_recommendation(
    report_id: UUID,
    rec_id: UUID,
    body: RecommendationReviewRequest,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Recommendation:
    quarry_id = await _quarry_id_for_report(report_id, db)
    await check_quarry_access(db, current_user.id, quarry_id, RoleLevel.BLASTER)

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
    quarry_id = await _quarry_id_for_report(report_id, db)
    await check_quarry_access(db, current_user.id, quarry_id, RoleLevel.USER)

    rec = (await db.execute(
        select(Recommendation).where(
            Recommendation.id == rec_id,
            Recommendation.report_id == report_id,
        )
    )).scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")

    from app.db.models.report import Comment
    comment = Comment(
        recommendation_id=rec.id,
        author_id=current_user.id,
        body=body.body,
    )
    db.add(comment)
    await db.flush()
    return comment
