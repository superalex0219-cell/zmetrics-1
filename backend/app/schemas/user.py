from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    # keycloak_sub deliberately NOT exposed (security.md §Output security):
    # the Keycloak subject is an internal identifier, never returned via the API.
    email: str
    full_name: str
    is_active: bool
    created_at: datetime


class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None


class QuarryAccessCreate(BaseModel):
    user_id: UUID
    quarry_id: UUID
    role_name: str  # "user", "surveyor", "blaster", "admin"


class QuarryAccessRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    quarry_id: UUID
    role_id: UUID
    granted_by_id: UUID | None
    revoked_at: datetime | None
    created_at: datetime
