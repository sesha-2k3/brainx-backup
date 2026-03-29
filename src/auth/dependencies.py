# Auth: FastAPI dependency that validates the Bearer token on protected routes
#
# Usage in any router:
#
#   from src.auth import get_current_user
#   from src.db.models import User
#
#   @router.get("/protected")
#   async def protected(current_user: User = Depends(get_current_user)):
#       return {"email": current_user.email}

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.service import decode_access_token
from src.db import get_db_unscoped  # unscoped: User is not tenant-scoped
from src.db.models import User

# Extracts the token from the "Authorization: Bearer <token>" header.
# auto_error=True means FastAPI returns 403 automatically if the header is absent.
_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db_unscoped),
) -> User:
    """
    Validate the Bearer JWT and return the corresponding User row.

    Raises HTTP 401 for any token problem (expired, invalid, missing user).
    Raises HTTP 403 if the user account has been deactivated.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user_id = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.InvalidTokenError:
        raise credentials_exception from None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user
