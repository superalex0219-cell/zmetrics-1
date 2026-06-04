"""Shared FastAPI dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_token
from app.db.models.user import UserProfile
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=True)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    """Decode JWT, look up or provision the UserProfile record."""
    try:
        payload = await decode_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub: str = payload.get("sub", "")
    email: str = payload.get("email", "")
    full_name: str = payload.get("name", payload.get("preferred_username", ""))

    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: missing sub")

    result = await db.execute(select(UserProfile).where(UserProfile.keycloak_sub == sub))
    user = result.scalar_one_or_none()

    if user is None:
        # Auto-provision profile on first login
        user = UserProfile(keycloak_sub=sub, email=email, full_name=full_name)
        db.add(user)
        await db.flush()

    elif not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")

    return user
