from uuid import UUID

from pydantic import BaseModel, ConfigDict


class QuarryCreate(BaseModel):
    name: str
    location_description: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class QuarryUpdate(BaseModel):
    name: str | None = None
    location_description: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class QuarryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    location_description: str | None
    latitude: float | None
    longitude: float | None


class SiteSectionCreate(BaseModel):
    quarry_id: UUID | None = None  # ignored: quarry_id comes from path param
    name: str
    block_number: str | None = None
    description: str | None = None


class SiteSectionUpdate(BaseModel):
    name: str | None = None
    block_number: str | None = None
    description: str | None = None


class SiteSectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quarry_id: UUID
    name: str
    block_number: str | None
    description: str | None
