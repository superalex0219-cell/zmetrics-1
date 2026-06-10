from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel, check_quarry_access, require_quarry_role
from app.db.models.blast import BlastEvent, Calibration, Device
from app.db.models.capture import CaptureSession
from app.db.models.passport import BlastPassport, PassportStatus
from app.db.models.user import UserProfile
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.blast import (
    BlastEventCreate,
    BlastEventRead,
    BlastEventUpdate,
    CaptureSessionCreate,
    CaptureSessionRead,
    CaptureSessionSummaryRead,
    FramePairSummary,
)
from app.schemas.common import PaginatedResponse
from app.services.audit import apply_update

router = APIRouter()


async def _get_passport_in_quarry(passport_id: UUID, quarry_id: UUID, db: AsyncSession) -> BlastPassport:
    from app.db.models.quarry import SiteSection
    passport = (await db.execute(
        select(BlastPassport)
        .join(SiteSection, SiteSection.id == BlastPassport.site_section_id)
        .where(BlastPassport.id == passport_id, SiteSection.quarry_id == quarry_id)
    )).scalar_one_or_none()
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found")
    return passport


@router.get("/blast-event", response_model=BlastEventRead)
async def get_blast_event(
    quarry_id: UUID,
    passport_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BlastEvent:
    await check_quarry_access(db, current_user.id, quarry_id, RoleLevel.USER)
    await _get_passport_in_quarry(passport_id, quarry_id, db)

    result = await db.execute(
        select(BlastEvent).where(BlastEvent.passport_id == passport_id)
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No blast event for this passport",
        )
    return event


@router.post(
    "/blast-event",
    response_model=BlastEventRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_blast_event(
    quarry_id: UUID,
    passport_id: UUID,
    body: BlastEventCreate,
    current_user: UserProfile = Depends(require_quarry_role(RoleLevel.BLASTER)),
    db: AsyncSession = Depends(get_db),
) -> BlastEvent:
    passport = await _get_passport_in_quarry(passport_id, quarry_id, db)
    if passport.status not in (PassportStatus.APPROVED, PassportStatus.ACTIVE):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot create blast event for passport in status {passport.status.value}",
        )

    existing_result = await db.execute(
        select(BlastEvent).where(BlastEvent.passport_id == passport_id)
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Blast event already exists for this passport",
        )

    event = BlastEvent(
        passport_id=passport_id,
        executed_by_id=current_user.id,
        **body.model_dump(),
    )
    db.add(event)
    await db.flush()
    return event


@router.patch("/blast-event", response_model=BlastEventRead)
async def patch_blast_event(
    quarry_id: UUID,
    passport_id: UUID,
    body: BlastEventUpdate,
    current_user: UserProfile = Depends(require_quarry_role(RoleLevel.BLASTER)),
    db: AsyncSession = Depends(get_db),
) -> BlastEvent:
    """EDIT-1: корректировка факта взрыва (дата, фактическая взрывчатка, погода, заметки)."""
    await _get_passport_in_quarry(passport_id, quarry_id, db)
    event = (await db.execute(
        select(BlastEvent).where(BlastEvent.passport_id == passport_id)
    )).scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No blast event for this passport",
        )
    changes = body.model_dump(exclude_unset=True)
    if changes:
        apply_update(
            db, actor_id=current_user.id, entity=event,
            entity_type="blast_event", changes=changes, passport_id=passport_id,
        )
    return event


@router.get("/blast-event/capture-sessions", response_model=PaginatedResponse[CaptureSessionRead])
async def list_capture_sessions(
    quarry_id: UUID,
    passport_id: UUID,
    page: int = 1,
    page_size: int = 20,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[CaptureSessionRead]:
    await check_quarry_access(db, current_user.id, quarry_id, RoleLevel.USER)
    await _get_passport_in_quarry(passport_id, quarry_id, db)

    event_result = await db.execute(
        select(BlastEvent).where(BlastEvent.passport_id == passport_id)
    )
    event = event_result.scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No blast event for this passport",
        )
    base = select(CaptureSession).where(CaptureSession.blast_event_id == event.id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    items = list((await db.execute(
        base.offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/blast-event/capture-summary",
    response_model=list[CaptureSessionSummaryRead],
)
async def blast_capture_summary(
    quarry_id: UUID,
    passport_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CaptureSessionSummaryRead]:
    """Photo list of a blast: sessions with per-frame-pair upload and job status."""
    from app.db.models.analysis import AnalysisJob
    from app.db.models.artifact import Artifact, ArtifactType

    await check_quarry_access(db, current_user.id, quarry_id, RoleLevel.USER)
    await _get_passport_in_quarry(passport_id, quarry_id, db)

    event = (await db.execute(
        select(BlastEvent).where(BlastEvent.passport_id == passport_id)
    )).scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No blast event for this passport",
        )

    sessions = list((await db.execute(
        select(CaptureSession)
        .where(CaptureSession.blast_event_id == event.id)
        .order_by(CaptureSession.capture_datetime.desc())
    )).scalars().all())
    if not sessions:
        return []
    session_ids = [s.id for s in sessions]

    artifacts = (await db.execute(
        select(Artifact.capture_session_id, Artifact.frame_index, Artifact.artifact_type)
        .where(
            Artifact.capture_session_id.in_(session_ids),
            Artifact.artifact_type.in_([ArtifactType.LEFT_FRAME, ArtifactType.RIGHT_FRAME]),
        )
    )).all()

    jobs = list((await db.execute(
        select(AnalysisJob)
        .where(AnalysisJob.capture_session_id.in_(session_ids))
        .order_by(AnalysisJob.queued_at)
    )).scalars().all())

    names = dict((await db.execute(
        select(UserProfile.id, UserProfile.full_name)
        .where(UserProfile.id.in_({s.captured_by_id for s in sessions}))
    )).all())

    # (session_id, frame_index) → {"left": bool, "right": bool}
    pairs: dict[tuple[UUID, int], dict[str, bool]] = {}
    for sid, frame_index, artifact_type in artifacts:
        slot = pairs.setdefault((sid, frame_index or 0), {"left": False, "right": False})
        slot["left" if artifact_type == ArtifactType.LEFT_FRAME else "right"] = True

    # Latest job per (session_id, frame_index) — jobs are ordered by queued_at
    latest_job: dict[tuple[UUID, int], AnalysisJob] = {}
    for job in jobs:
        latest_job[(job.capture_session_id, job.frame_index or 0)] = job

    summaries: list[CaptureSessionSummaryRead] = []
    for session in sessions:
        frames = []
        for (sid, frame_index), slot in sorted(pairs.items()):
            if sid != session.id:
                continue
            job = latest_job.get((sid, frame_index))
            frames.append(FramePairSummary(
                frame_index=frame_index,
                has_left=slot["left"],
                has_right=slot["right"],
                job_id=job.id if job else None,
                job_status=job.status.value if job else None,
            ))
        session_jobs = [j for j in jobs if j.capture_session_id == session.id]
        summaries.append(CaptureSessionSummaryRead(
            id=session.id,
            capture_datetime=session.capture_datetime,
            captured_by_id=session.captured_by_id,
            captured_by_name=names.get(session.captured_by_id),
            device_id=session.device_id,
            calibration_id=session.calibration_id,
            frame_count=session.frame_count,
            notes=session.notes,
            frames=frames,
            jobs_total=len(session_jobs),
            jobs_completed=sum(1 for j in session_jobs if j.status.value == "completed"),
            jobs_failed=sum(1 for j in session_jobs if j.status.value == "failed"),
        ))
    return summaries


@router.post(
    "/blast-event/capture-sessions",
    response_model=CaptureSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_capture_session(
    quarry_id: UUID,
    passport_id: UUID,
    body: CaptureSessionCreate,
    current_user: UserProfile = Depends(require_quarry_role(RoleLevel.SURVEYOR)),
    db: AsyncSession = Depends(get_db),
) -> CaptureSession:
    await _get_passport_in_quarry(passport_id, quarry_id, db)

    event_result = await db.execute(
        select(BlastEvent).where(BlastEvent.passport_id == passport_id)
    )
    event = event_result.scalar_one_or_none()
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No blast event for this passport",
        )

    device_result = await db.execute(select(Device).where(Device.id == body.device_id))
    if device_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    cal_result = await db.execute(
        select(Calibration).where(Calibration.id == body.calibration_id)
    )
    if cal_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Calibration not found"
        )

    session = CaptureSession(
        blast_event_id=event.id,
        captured_by_id=current_user.id,
        device_id=body.device_id,
        calibration_id=body.calibration_id,
        capture_datetime=body.capture_datetime or datetime.now(tz=timezone.utc),
        frame_count=0,
        notes=body.notes,
    )
    db.add(session)
    await db.flush()
    return session
