import hashlib
import io
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import RoleLevel, check_quarry_access
from app.db.models.artifact import Artifact, ArtifactType
from app.db.models.capture import CaptureSession
from app.db.models.user import UserProfile
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.blast import ArtifactRead, ArtifactUrlRead
from app.schemas.common import PaginatedResponse
from app.services.storage import get_storage_service

router = APIRouter()


async def _quarry_id_for_session(session_id: UUID, db: AsyncSession) -> UUID:
    from app.db.models.blast import BlastEvent
    from app.db.models.passport import BlastPassport
    from app.db.models.quarry import SiteSection
    result = await db.execute(
        select(SiteSection.quarry_id)
        .join(BlastPassport, BlastPassport.site_section_id == SiteSection.id)
        .join(BlastEvent, BlastEvent.passport_id == BlastPassport.id)
        .join(CaptureSession, CaptureSession.blast_event_id == BlastEvent.id)
        .where(CaptureSession.id == session_id)
    )
    quarry_id = result.scalar_one_or_none()
    if quarry_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capture session not found")
    return quarry_id


_FRAMES_BUCKET = "zmetrics-frames"
_ARTIFACTS_BUCKET = "zmetrics-artifacts"
_FRAME_TYPES = {ArtifactType.LEFT_FRAME, ArtifactType.RIGHT_FRAME}
_ALLOWED_FRAME_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}
_PRESIGNED_URL_TTL = 3600


@router.get("/{session_id}/artifacts", response_model=PaginatedResponse[ArtifactRead])
async def list_artifacts(
    session_id: UUID,
    page: int = 1,
    page_size: int = 20,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ArtifactRead]:
    quarry_id = await _quarry_id_for_session(session_id, db)
    await check_quarry_access(db, current_user.id, quarry_id, RoleLevel.USER)
    base = select(Artifact).where(Artifact.capture_session_id == session_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    items = list((await db.execute(
        base.offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/{session_id}/artifacts",
    response_model=ArtifactRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_artifact(
    session_id: UUID,
    artifact_type: ArtifactType = Form(...),
    frame_index: int | None = Form(None),
    file: UploadFile = File(...),
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Artifact:
    quarry_id = await _quarry_id_for_session(session_id, db)
    await check_quarry_access(db, current_user.id, quarry_id, RoleLevel.SURVEYOR)

    # Session confirmed to exist by _quarry_id_for_session above
    session = (await db.execute(
        select(CaptureSession).where(CaptureSession.id == session_id)
    )).scalar_one()

    content_type = file.content_type or "application/octet-stream"
    if artifact_type in _FRAME_TYPES and content_type not in _ALLOWED_FRAME_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Frame artifacts require JPEG or PNG, got {content_type}",
        )

    content = await file.read()

    if artifact_type in _FRAME_TYPES:
        if not (content[:3] == b'\xff\xd8\xff' or content[:8] == b'\x89PNG\r\n\x1a\n'):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Frame content does not match JPEG or PNG magic bytes",
            )
    checksum = hashlib.sha256(content).hexdigest()

    bucket = _FRAMES_BUCKET if artifact_type in _FRAME_TYPES else _ARTIFACTS_BUCKET
    artifact_id = uuid.uuid4()
    ext = _ext_from_content_type(content_type)
    idx_part = f"_{frame_index:04d}" if frame_index is not None else ""
    key = f"sessions/{session_id}/{artifact_type.value}/{artifact_id}{idx_part}{ext}"

    get_storage_service().upload_file(bucket, key, io.BytesIO(content), content_type)

    artifact = Artifact(
        id=artifact_id,
        capture_session_id=session_id,
        artifact_type=artifact_type,
        storage_bucket=bucket,
        storage_key=key,
        file_size_bytes=len(content),
        content_type=content_type,
        checksum_sha256=checksum,
        frame_index=frame_index,
    )
    db.add(artifact)

    if artifact_type in _FRAME_TYPES:
        session.frame_count = (session.frame_count or 0) + 1

    await db.flush()
    return artifact


@router.get("/{session_id}/artifacts/{artifact_id}/url", response_model=ArtifactUrlRead)
async def get_artifact_url(
    session_id: UUID,
    artifact_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArtifactUrlRead:
    quarry_id = await _quarry_id_for_session(session_id, db)
    await check_quarry_access(db, current_user.id, quarry_id, RoleLevel.USER)

    result = await db.execute(
        select(Artifact).where(
            Artifact.id == artifact_id,
            Artifact.capture_session_id == session_id,
        )
    )
    artifact = result.scalar_one_or_none()
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found"
        )

    url = get_storage_service().get_presigned_url(
        artifact.storage_bucket, artifact.storage_key, expires_in=_PRESIGNED_URL_TTL
    )
    return ArtifactUrlRead(url=url, expires_in=_PRESIGNED_URL_TTL)


def _ext_from_content_type(content_type: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
    }.get(content_type, ".bin")
