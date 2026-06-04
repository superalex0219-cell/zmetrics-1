from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.models.passport import PassportStatus


class BlastPassportCreate(BaseModel):
    site_section_id: UUID
    blast_date_planned: datetime | None = None
    explosive_type: str | None = None
    total_explosive_kg: float | None = None
    number_of_holes: int | None = None
    hole_diameter_mm: float | None = None
    hole_depth_m: float | None = None
    burden_m: float | None = None
    spacing_m: float | None = None
    stemming_m: float | None = None
    target_p80_mm: float | None = None
    notes: str | None = None


class BlastPassportUpdate(BlastPassportCreate):
    site_section_id: UUID | None = None


class BlastPassportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    site_section_id: UUID
    created_by_id: UUID
    approved_by_id: UUID | None
    revision_number: int
    superseded_by_id: UUID | None
    status: PassportStatus
    blast_date_planned: datetime | None
    explosive_type: str | None
    total_explosive_kg: float | None
    number_of_holes: int | None
    hole_diameter_mm: float | None
    hole_depth_m: float | None
    burden_m: float | None
    spacing_m: float | None
    stemming_m: float | None
    target_p80_mm: float | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PassportReviewRequest(BaseModel):
    notes: str | None = None
