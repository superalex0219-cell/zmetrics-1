from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    # keycloak_sub deliberately NOT exposed (security.md §Output security):
    # the Keycloak subject is an internal identifier, never returned via the API.
    email: str
    full_name: str
    is_active: bool
    created_at: datetime


class UserProfileCreate(BaseModel):
    email: EmailStr
    full_name: str
    # No password field — a temporary one is generated server-side and returned once.


class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None  # NEW — synced to Keycloak identity
    is_active: bool | None = None  # synced to Keycloak `enabled`


class UserCreateResult(BaseModel):
    user: UserProfileRead
    temporary_password: str  # shown ONCE; never stored, never logged


class PasswordResetResult(BaseModel):
    temporary_password: str  # shown ONCE; never stored, never logged


class UserQuarryAccessRead(BaseModel):
    access_id: UUID
    quarry_id: UUID
    quarry_name: str
    role_name: str
    role_level: int


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
