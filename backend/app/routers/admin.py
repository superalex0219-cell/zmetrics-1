from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import require_any_admin
from app.config import get_settings
from app.db.models.audit import AuditLog
from app.db.models.quarry import Quarry
from app.db.models.user import QuarryUserAccess, Role, UserProfile
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.common import PaginatedResponse
from app.schemas.user import (
    PasswordResetResult,
    QuarryAccessCreate,
    QuarryAccessRead,
    UserCreateResult,
    UserProfileCreate,
    UserProfileRead,
    UserProfileUpdate,
    UserQuarryAccessRead,
)
from app.services.keycloak_admin import (
    KeycloakAdminClient,
    KeycloakAdminError,
    generate_temp_password,
    get_keycloak_admin_client,
)


def _require_user_mgmt() -> None:
    """503 when admin user-management against Keycloak is not enabled.

    Ships the create / reset-password / identity-sync paths dark so they only
    run where the service account is configured.
    """
    if not get_settings().enable_admin_user_management:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User management is not enabled",
        )


def _map_kc_error(exc: KeycloakAdminError) -> HTTPException:
    """Map a Keycloak admin failure to a client response without leaking internals."""
    if exc.status_code == 409:
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    if exc.status_code == 400:
        # Keycloak rejected the data (e.g. non-ASCII or malformed email/username).
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identity provider rejected the data: email/username must be a valid "
                   "ASCII e-mail address",
        )
    if exc.status_code in (502, 503):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Identity provider unavailable",
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Identity provider error",
    )


class DevSeedResult(BaseModel):
    quarry_id: UUID
    section_id: UUID
    passport_id: UUID
    report_id: UUID
    recommendation_id: UUID
    already_existed: bool

router = APIRouter()


@router.get("/users", response_model=PaginatedResponse[UserProfileRead])
async def list_users(
    page: int = 1,
    page_size: int = 50,
    current_user: UserProfile = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[UserProfileRead]:
    from sqlalchemy import func
    base = select(UserProfile).where(UserProfile.is_active.is_(True))
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    items = list((await db.execute(
        base.offset((page - 1) * page_size).limit(page_size)
    )).scalars().all())
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/users", response_model=UserCreateResult, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserProfileCreate,
    current_user: UserProfile = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
    kc: KeycloakAdminClient = Depends(get_keycloak_admin_client),
) -> UserCreateResult:
    """Create a Keycloak account, then mirror it as a local UserProfile.

    The temporary password is generated server-side and returned ONCE — it is
    never persisted, logged, or written to the audit trail.
    """
    _require_user_mgmt()

    temp_password = generate_temp_password()
    try:
        sub = await kc.create_user(
            email=body.email, full_name=body.full_name, temp_password=temp_password
        )
    except KeycloakAdminError as exc:
        raise _map_kc_error(exc)

    new = UserProfile(
        keycloak_sub=sub,
        email=body.email,
        full_name=body.full_name,
        is_active=True,
    )
    db.add(new)
    try:
        # Savepoint so a local uniqueness failure doesn't poison the surrounding
        # transaction (and doesn't roll back unrelated work in tests).
        async with db.begin_nested():
            await db.flush()
    except IntegrityError:
        # Local mirror failed after Keycloak created the account → neutralize the
        # orphan so a disabled account can't linger. Best-effort; never fatal.
        try:
            await kc.update_user(sub=sub, enabled=False)
        except KeycloakAdminError:
            pass
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    db.add(AuditLog(
        actor_id=current_user.id,
        entity_type="user_profile",
        entity_id=new.id,
        action="user_created",
        new_value={"email": body.email},  # NEVER include the temporary password
    ))
    return UserCreateResult(
        user=UserProfileRead.model_validate(new),
        temporary_password=temp_password,
    )


@router.patch("/users/{user_id}", response_model=UserProfileRead)
async def update_user(
    user_id: UUID,
    body: UserProfileUpdate,
    current_user: UserProfile = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
    kc: KeycloakAdminClient = Depends(get_keycloak_admin_client),
) -> UserProfile:
    result = await db.execute(select(UserProfile).where(UserProfile.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    mgmt_enabled = get_settings().enable_admin_user_management
    # Email is an identity field — refuse to edit it locally when we can't sync
    # it to Keycloak, or the app DB and the IdP would diverge.
    if body.email is not None and not mgmt_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User management is not enabled",
        )

    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(user, field, value)
    db.add(AuditLog(
        actor_id=current_user.id,
        entity_type="user_profile",
        entity_id=user_id,
        action="user_updated",
        new_value=changes,
    ))

    if mgmt_enabled and changes:
        try:
            await kc.update_user(
                sub=user.keycloak_sub,
                email=body.email,
                full_name=body.full_name,
                enabled=body.is_active,
            )
        except KeycloakAdminError as exc:
            raise _map_kc_error(exc)
    return user


@router.post("/users/{user_id}/reset-password", response_model=PasswordResetResult)
async def reset_user_password(
    user_id: UUID,
    current_user: UserProfile = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
    kc: KeycloakAdminClient = Depends(get_keycloak_admin_client),
) -> PasswordResetResult:
    """Set a one-time temporary password in Keycloak; return it ONCE."""
    _require_user_mgmt()

    result = await db.execute(select(UserProfile).where(UserProfile.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    temp_password = generate_temp_password()
    try:
        await kc.reset_password(sub=user.keycloak_sub, temp_password=temp_password)
    except KeycloakAdminError as exc:
        raise _map_kc_error(exc)

    db.add(AuditLog(
        actor_id=current_user.id,
        entity_type="user_profile",
        entity_id=user.id,
        action="user_password_reset",  # NEVER include the password in old/new_value
    ))
    return PasswordResetResult(temporary_password=temp_password)


@router.get("/users/{user_id}/access", response_model=list[UserQuarryAccessRead])
async def get_user_access(
    user_id: UUID,
    current_user: UserProfile = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
) -> list[UserQuarryAccessRead]:
    """List a user's active per-quarry roles (excludes revoked + soft-deleted quarries)."""
    rows = (await db.execute(
        select(QuarryUserAccess.id, Quarry.id, Quarry.name, Role.name, Role.level)
        .join(Quarry, Quarry.id == QuarryUserAccess.quarry_id)
        .join(Role, Role.id == QuarryUserAccess.role_id)
        .where(
            QuarryUserAccess.user_id == user_id,
            QuarryUserAccess.revoked_at.is_(None),
            Quarry.deleted_at.is_(None),
        )
        .order_by(Quarry.name)
    )).all()
    return [
        UserQuarryAccessRead(
            access_id=access_id,
            quarry_id=quarry_id,
            quarry_name=quarry_name,
            role_name=role_name,
            role_level=role_level,
        )
        for access_id, quarry_id, quarry_name, role_name, role_level in rows
    ]


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: UUID,
    current_user: UserProfile = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
    kc: KeycloakAdminClient = Depends(get_keycloak_admin_client),
) -> None:
    result = await db.execute(select(UserProfile).where(UserProfile.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )
    user.is_active = False
    db.add(AuditLog(
        actor_id=current_user.id,
        entity_type="user_profile",
        entity_id=user_id,
        action="user_deactivated",
    ))

    # Disable the Keycloak account too, so a deactivated user cannot log in.
    if get_settings().enable_admin_user_management:
        try:
            await kc.update_user(sub=user.keycloak_sub, enabled=False)
        except KeycloakAdminError as exc:
            raise _map_kc_error(exc)


@router.post("/quarries/{quarry_id}/access", response_model=QuarryAccessRead, status_code=status.HTTP_201_CREATED)
async def grant_access(
    quarry_id: UUID,
    body: QuarryAccessCreate,
    current_user: UserProfile = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
) -> QuarryUserAccess:
    role_result = await db.execute(select(Role).where(Role.name == body.role_name))
    role = role_result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown role: {body.role_name}")

    # Upsert: a user has at most one active role per quarry (uq_quarry_user_active).
    # Granting over an existing role means "change the role", not a 500.
    existing = (await db.execute(
        select(QuarryUserAccess).where(
            QuarryUserAccess.user_id == body.user_id,
            QuarryUserAccess.quarry_id == quarry_id,
            QuarryUserAccess.revoked_at.is_(None),
        )
    )).scalar_one_or_none()
    if existing is not None:
        if existing.role_id == role.id:
            return existing  # идемпотентно: роль уже выдана
        existing.revoked_at = datetime.now(tz=timezone.utc)
        db.add(AuditLog(
            actor_id=current_user.id,
            entity_type="quarry_user_access",
            entity_id=existing.id,
            action="role_revoked",
            old_value={"quarry_id": str(quarry_id), "reason": "role_changed"},
        ))
        # UPDATE must hit the DB before the INSERT below to satisfy the partial
        # unique index within the same transaction.
        await db.flush()

    access = QuarryUserAccess(
        user_id=body.user_id,
        quarry_id=quarry_id,
        role_id=role.id,
        granted_by_id=current_user.id,
    )
    db.add(access)
    await db.flush()

    db.add(AuditLog(
        actor_id=current_user.id,
        entity_type="quarry_user_access",
        entity_id=access.id,
        action="role_assigned",
        new_value={"user_id": str(body.user_id), "role": body.role_name, "quarry_id": str(quarry_id)},
    ))
    return access


@router.delete("/quarries/{quarry_id}/access/{access_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_access(
    quarry_id: UUID,
    access_id: UUID,
    current_user: UserProfile = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    from datetime import datetime, timezone
    result = await db.execute(
        select(QuarryUserAccess).where(
            QuarryUserAccess.id == access_id,
            QuarryUserAccess.quarry_id == quarry_id,
        )
    )
    access = result.scalar_one_or_none()
    if access is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access record not found")
    access.revoked_at = datetime.now(tz=timezone.utc)
    db.add(AuditLog(
        actor_id=current_user.id,
        entity_type="quarry_user_access",
        entity_id=access.id,
        action="role_revoked",
        old_value={"quarry_id": str(quarry_id)},
    ))


@router.post("/dev-seed", response_model=DevSeedResult, status_code=status.HTTP_201_CREATED)
async def dev_seed(
    current_user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DevSeedResult:
    """Idempotent: create demo quarry/analysis chain and grant calling user admin access.
    Safe to call multiple times — skips creation if 'Demo Quarry' already exists."""
    # SECURITY: this endpoint grants the caller admin on a quarry, so it is gated
    # behind an explicit dev flag. 404 (not 403) keeps it undiscoverable in prod.
    if not get_settings().enable_dev_seed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    from app.db.models.analysis import AnalysisJob, AnalysisResult, JobStatus, ModelVersion
    from app.db.models.blast import BlastEvent, Calibration, Device
    from app.db.models.capture import CaptureSession
    from app.db.models.passport import BlastPassport, PassportStatus
    from app.db.models.quarry import Quarry, SiteSection
    from app.db.models.report import Recommendation, RecommendationStatus, Report

    existing_quarry = (await db.execute(
        select(Quarry).where(Quarry.name == "Demo Quarry", Quarry.deleted_at.is_(None))
    )).scalar_one_or_none()

    if existing_quarry is not None:
        # Return existing report if the chain is complete
        report = (await db.execute(
            select(Report)
            .join(AnalysisResult, AnalysisResult.id == Report.analysis_result_id)
            .join(AnalysisJob, AnalysisJob.id == AnalysisResult.job_id)
            .join(CaptureSession, CaptureSession.id == AnalysisJob.capture_session_id)
            .join(BlastEvent, BlastEvent.id == CaptureSession.blast_event_id)
            .join(BlastPassport, BlastPassport.id == BlastEvent.passport_id)
            .join(SiteSection, SiteSection.id == BlastPassport.site_section_id)
            .where(SiteSection.quarry_id == existing_quarry.id)
        )).scalar_one_or_none()

        section = (await db.execute(
            select(SiteSection).where(SiteSection.quarry_id == existing_quarry.id)
        )).scalars().first()

        if report and section:
            rec = (await db.execute(
                select(Recommendation).where(Recommendation.report_id == report.id)
            )).scalars().first()

            # Ensure calling user has access
            access_exists = (await db.execute(
                select(QuarryUserAccess).where(
                    QuarryUserAccess.user_id == current_user.id,
                    QuarryUserAccess.quarry_id == existing_quarry.id,
                    QuarryUserAccess.revoked_at.is_(None),
                )
            )).scalar_one_or_none()
            if access_exists:
                db.add(AuditLog(
                    actor_id=current_user.id,
                    entity_type="quarry_user_access",
                    entity_id=access_exists.id,
                    action="role_assigned",
                    new_value={"role": "admin", "quarry_id": str(existing_quarry.id)},
                ))
            else:
                admin_role = (await db.execute(
                    select(Role).where(Role.name == "admin")
                )).scalar_one_or_none()
                if admin_role:
                    new_access = QuarryUserAccess(
                        user_id=current_user.id,
                        quarry_id=existing_quarry.id,
                        role_id=admin_role.id,
                        granted_by_id=current_user.id,
                    )
                    db.add(new_access)
                    await db.flush()
                    db.add(AuditLog(
                        actor_id=current_user.id,
                        entity_type="quarry_user_access",
                        entity_id=new_access.id,
                        action="role_assigned",
                        new_value={"role": "admin", "quarry_id": str(existing_quarry.id)},
                    ))

            passport = (await db.execute(
                select(BlastPassport).where(BlastPassport.site_section_id == section.id)
            )).scalars().first()

            return DevSeedResult(
                quarry_id=existing_quarry.id,
                section_id=section.id,
                passport_id=passport.id if passport else section.id,
                report_id=report.id,
                recommendation_id=rec.id if rec else report.id,
                already_existed=True,
            )

    # ── Build the full demo chain ─────────────────────────────────────────────
    now = datetime.now(tz=timezone.utc)

    quarry = Quarry(name="Demo Quarry", location_description="Seeded for development")
    db.add(quarry)
    await db.flush()

    section = SiteSection(quarry_id=quarry.id, name="Block A", block_number="A-001")
    db.add(section)
    await db.flush()

    # Grant caller admin access
    admin_role = (await db.execute(select(Role).where(Role.name == "admin"))).scalar_one_or_none()
    if admin_role is None:
        admin_role = Role(name="admin", level=4)
        db.add(admin_role)
        await db.flush()

    access = QuarryUserAccess(
        user_id=current_user.id,
        quarry_id=quarry.id,
        role_id=admin_role.id,
        granted_by_id=current_user.id,
    )
    db.add(access)
    await db.flush()
    db.add(AuditLog(
        actor_id=current_user.id,
        entity_type="quarry_user_access",
        entity_id=access.id,
        action="role_assigned",
        new_value={"role": "admin", "quarry_id": str(quarry.id)},
    ))

    passport = BlastPassport(
        site_section_id=section.id,
        created_by_id=current_user.id,
        approved_by_id=current_user.id,
        status=PassportStatus.ACTIVE,
        explosive_type="ANFO",
        total_explosive_kg=2400.0,
        burden_m=3.5,
        spacing_m=4.0,
        hole_depth_m=12.0,
        hole_diameter_mm=115.0,
        number_of_holes=24,
        stemming_m=3.0,
        target_p80_mm=500.0,
    )
    db.add(passport)
    await db.flush()

    blast_event = BlastEvent(
        passport_id=passport.id,
        executed_by_id=current_user.id,
        blast_datetime=now,
        actual_explosive_kg=2380.0,
        notes="Demo blast event — seeded",
    )
    db.add(blast_event)
    await db.flush()

    device = Device(serial_number="DEMO-ZED2-0001", model="ZED 2", firmware_version="4.0.8")
    db.add(device)
    await db.flush()

    calibration = Calibration(
        device_id=device.id,
        calibrated_by_id=current_user.id,
        left_camera_matrix={"fx": 699.7, "fy": 699.7, "cx": 640.0, "cy": 360.0},
        right_camera_matrix={"fx": 699.7, "fy": 699.7, "cx": 640.0, "cy": 360.0},
        left_dist_coeffs={"k1": -0.17, "k2": 0.03, "p1": 0.0, "p2": 0.0, "k3": 0.0},
        right_dist_coeffs={"k1": -0.17, "k2": 0.03, "p1": 0.0, "p2": 0.0, "k3": 0.0},
        rotation_matrix={"data": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]},
        translation_vector={"data": [-0.12, 0.0, 0.0]},
        baseline_mm=120.0,
        image_width_px=1280,
        image_height_px=720,
    )
    db.add(calibration)
    await db.flush()

    capture_session = CaptureSession(
        blast_event_id=blast_event.id,
        device_id=device.id,
        calibration_id=calibration.id,
        captured_by_id=current_user.id,
        capture_datetime=now,
        frame_count=12,
        notes="Demo capture — seeded",
    )
    db.add(capture_session)
    await db.flush()

    model_ver = ModelVersion(
        name="Mock Pipeline",
        version_tag="mock-v1",
        model_type="mock",
        is_active=True,
        metrics={"note": "synthetic data"},
    )
    db.add(model_ver)
    await db.flush()

    job = AnalysisJob(
        capture_session_id=capture_session.id,
        model_version_id=model_ver.id,
        status=JobStatus.COMPLETED,
        queued_at=now,
        started_at=now,
        completed_at=now,
        pipeline_log={"note": "⚠ Mock pipeline — results are synthetic"},
    )
    db.add(job)
    await db.flush()

    analysis_result = AnalysisResult(
        job_id=job.id,
        p10_mm=120.5,
        p50_mm=345.2,
        p80_mm=580.8,
        rosin_rammler_n=1.42,
        rosin_rammler_xc=390.0,
        uniformity_index=1.18,
        oversize_percent=8.3,
        fines_percent=4.1,
        total_particles_counted=1847,
        total_volume_m3=12450.0,
        confidence_score=0.87,
        size_distribution=[
            {"size_mm": 50, "cumulative_passing_pct": 4.2},
            {"size_mm": 100, "cumulative_passing_pct": 10.1},
            {"size_mm": 200, "cumulative_passing_pct": 28.4},
            {"size_mm": 350, "cumulative_passing_pct": 51.9},
            {"size_mm": 500, "cumulative_passing_pct": 71.6},
            {"size_mm": 700, "cumulative_passing_pct": 88.2},
            {"size_mm": 1000, "cumulative_passing_pct": 97.4},
        ],
    )
    db.add(analysis_result)
    await db.flush()

    report = Report(
        analysis_result_id=analysis_result.id,
        generated_by_id=current_user.id,
        report_type="granulometric",
        title="Demo Granulometric Analysis — Block A",
    )
    db.add(report)
    await db.flush()

    recommendation = Recommendation(
        report_id=report.id,
        generated_by_id=current_user.id,
        recommendation_text=(
            "⚠ Mock pipeline — results are synthetic. "
            "P80=580mm exceeds target of 500mm. "
            "Consider reducing burden by 0.3m or increasing explosive factor by 10%."
        ),
        parameter_suggestions={"burden_m": 3.2, "specific_charge_kg_m3": 0.42},
        status=RecommendationStatus.REQUIRES_HUMAN_REVIEW,
    )
    db.add(recommendation)
    await db.flush()

    return DevSeedResult(
        quarry_id=quarry.id,
        section_id=section.id,
        passport_id=passport.id,
        report_id=report.id,
        recommendation_id=recommendation.id,
        already_existed=False,
    )


@router.get("/audit-logs", response_model=list[dict])
async def list_audit_logs(
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    page: int = 1,
    page_size: int = 50,
    current_user: UserProfile = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    query = select(AuditLog).order_by(AuditLog.occurred_at.desc())
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "actor_id": str(log.actor_id) if log.actor_id else None,
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id),
            "action": log.action,
            "occurred_at": log.occurred_at.isoformat(),
            "old_value": log.old_value,
            "new_value": log.new_value,
        }
        for log in logs
    ]
