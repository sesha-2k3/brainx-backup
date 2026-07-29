# Auth: Password hashing and JWT token logic
#
# Dependencies:
#   pip install bcrypt PyJWT
#   (passlib is NOT used — it breaks with bcrypt 4.x)

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from src.config import get_settings

settings = get_settings()


# ── Password helpers ──────────────────────────────────────────────────────────


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the given plain-text password.

    bcrypt silently truncates input at 72 bytes. We raise early so the user
    isn't surprised that extra characters beyond 72 are ignored.
    """
    encoded = plain.encode("utf-8")
    if len(encoded) > 72:
        raise ValueError("Password must be 72 characters or fewer")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ── JWT helpers ───────────────────────────────────────────────────────────────


def create_access_token(subject: str, *, remember_me: bool = False) -> str:
    """
    Create a signed JWT containing the user's ID as the subject claim.

    Args:
        subject: The user's ID (str UUID).
        remember_me: When True, issue a long-lived token
            (settings.remember_me_expire_minutes) instead of the default.

    Returns:
        A compact JWT string.
    """
    lifetime = (
        settings.remember_me_expire_minutes if remember_me else settings.access_token_expire_minutes
    )
    expire = datetime.now(UTC) + timedelta(minutes=lifetime)
    payload = {
        "sub": subject,  # who the token represents
        "exp": expire,  # expiry timestamp (PyJWT validates this automatically)
        "iat": datetime.now(UTC),  # issued-at
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """
    Decode and validate a JWT, returning the subject (user ID).

    Raises:
        jwt.ExpiredSignatureError: if the token has expired.
        jwt.InvalidTokenError:     if the token is malformed or has a bad signature.
    """
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    subject: str | None = payload.get("sub")
    if subject is None:
        raise jwt.InvalidTokenError("Token payload missing 'sub' claim")
    return subject
