"""BlastPassport business logic: revision management and status transitions."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import AuditLog
from app.db.models.passport import BlastPassport, PassportStatus


async def create_revision(
    db: AsyncSession,
    original: BlastPassport,
    updated_fields: dict[str, Any],
    actor_id: uuid.UUID,
) -> BlastPassport:
    """
    Create a new revision of a passport.

    Marks the original as SUPERSEDED, sets superseded_by_id, creates a new
    BlastPassport with revision_number + 1.
    """
    new_revision = BlastPassport(
        site_section_id=original.site_section_id,
        created_by_id=actor_id,
        revision_number=original.revision_number + 1,
        status=PassportStatus.DRAFT,
        # Copy all blast design fields from original
        blast_date_planned=original.blast_date_planned,
        explosive_type=original.explosive_type,
        total_explosive_kg=original.total_explosive_kg,
        number_of_holes=original.number_of_holes,
        hole_diameter_mm=original.hole_diameter_mm,
        hole_depth_m=original.hole_depth_m,
        burden_m=original.burden_m,
        spacing_m=original.spacing_m,
        stemming_m=original.stemming_m,
        target_p80_mm=original.target_p80_mm,
        notes=original.notes,
    )

    # Apply any updates to the new revision
    for field, value in updated_fields.items():
        if hasattr(new_revision, field) and value is not None:
            setattr(new_revision, field, value)

    db.add(new_revision)
    await db.flush()  # get new_revision.id

    # Mark original as superseded
    original.status = PassportStatus.SUPERSEDED
    original.superseded_by_id = new_revision.id

    # Audit log for the revision event
    db.add(AuditLog(
        actor_id=actor_id,
        entity_type="blast_passport",
        entity_id=original.id,
        action="revision_created",
        old_value={"revision_number": original.revision_number, "status": "active"},
        new_value={"superseded_by_id": str(new_revision.id), "status": "superseded"},
        passport_id=original.id,
    ))

    return new_revision
