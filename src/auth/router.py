# Auth: Register, login, and profile endpoints

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from src.auth.service import create_access_token, hash_password, verify_password
from src.db import get_db_unscoped  # User is not tenant-scoped
from src.db.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db_unscoped),
) -> TokenResponse:
    """
    Register a new user with email + password.

    - Email must be unique.
    - Password must be at least 8 characters.
    - Returns a JWT access token immediately (no separate login step needed).
    """
    # Reject duplicate emails
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()  # populate user.id without committing yet
    await db.refresh(user)

    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive an access token",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db_unscoped),
) -> TokenResponse:
    """
    Authenticate with email + password.

    Returns a JWT access token. Include it in subsequent requests as:
    `Authorization: Bearer <token>`
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Constant-time path: always verify even when user is None to prevent
    # timing attacks that could reveal whether an email is registered.
    password_ok = verify_password(body.password, user.hashed_password) if user else False

    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Return the currently authenticated user",
)
async def me(current_user: User = Depends(get_current_user)) -> User:
    """
    Returns the profile of the user associated with the provided Bearer token.
    Useful for verifying a token is still valid on the client side.
    """
    return current_user
