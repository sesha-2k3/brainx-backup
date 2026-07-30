"""
Test: authentication.

This file also puts the `authed_client` / `anon_client` fixtures to work. They
were added to tests/test_api/conftest.py and never used, which is why that file
itself sits at 46%.

STRUCTURE
---------
Pure functions first (hashing, JWT encode/decode) with no doubles at all, then
schema validation, then the HTTP surface. The token-failure cases build tokens by
hand rather than mocking the clock, so the tests exercise real PyJWT validation.

WHY THE ODD ASSERTIONS ON STATUS CODES
--------------------------------------
Two results look wrong and are not:

  - A request with NO Authorization header is rejected by HTTPBearer itself
    (auto_error=True), before get_current_user's body runs. Current FastAPI
    returns 401 for this; older releases returned 403. TestProtectedRoutesRequireAuth
    accepts either, because the point there is unreachability, not the exact code.
  - An unknown email and a wrong password both return 401 with an identical body.
    That is deliberate: differing responses would let an attacker enumerate
    registered addresses.
"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pydantic import ValidationError

from src.auth.schemas import LoginRequest, RegisterRequest
from src.auth.service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from src.config import get_settings
from src.db.models import User


def _make_token(payload: dict) -> str:
    """Sign an arbitrary payload with the app's real key and algorithm."""
    s = get_settings()
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


# Fixed ids for readable failures. Each one deliberately contains a hex LETTER.
#
# SQLAlchemy stores a UUID as its 32-char hex with hyphens stripped, and on SQLite
# the "UUID" column type gets NUMERIC affinity. An all-digit hex is therefore a
# well-formed integer literal, overflows int64, and comes back as a float:
#
#     "11111111-1111-4111-8111-111111111111"
#       -> "11111111111141118111111111111111" -> 1.1111111111141117e+31
#
# which then crashes the Uuid RESULT processor deep inside an unrelated request.
# tests/conftest.py now forces TEXT affinity for UUID columns, which fixes the
# root cause; keeping a letter in each id means these tests do not silently
# depend on that remap staying in place.


async def _make_user(db, *, user_id: str, email: str, password: str, is_active: bool = True):
    """
    Insert a User, supplying created_at/updated_at explicitly.

    Those columns use server_default=func.now(), so omitting them leaves the
    attributes unloaded after flush and forces a post-INSERT fetch. Supplying
    them keeps the object fully populated, which makes the fixture cheaper and
    its state obvious.

    NOTE: this is NOT what caused the 'float' object has no attribute 'replace'
    error. That was the UUID affinity problem described above the function — the
    id column, not these timestamps. Kept because it is still the better way to
    build a fixture row, but it was not the fix.
    """
    now = datetime.now(UTC)
    user = User(
        id=user_id,
        email=email,
        hashed_password=hash_password(password),
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    await db.flush()
    return user


# ---------------------------------------------------------------------------
# Pure logic: password hashing (zero doubles)
# ---------------------------------------------------------------------------
class TestPasswordHashing:
    def test_hash_is_not_the_plaintext(self):
        hashed = hash_password("correct horse battery")
        assert hashed != "correct horse battery"
        assert hashed.startswith("$2")

    def test_same_password_hashes_differently_each_time(self):
        """bcrypt salts each hash, so identical passwords must not collide."""
        assert hash_password("same-password") != hash_password("same-password")

    def test_verify_accepts_the_correct_password(self):
        assert verify_password("s3cret-password", hash_password("s3cret-password")) is True

    def test_verify_rejects_the_wrong_password(self):
        assert verify_password("wrong-password", hash_password("s3cret-password")) is False

    def test_verify_returns_false_rather_than_raising_on_a_malformed_hash(self):
        """
        Covers the bare `except Exception: return False` in verify_password.

        It matters for the login path: a corrupted or truncated hash column must
        produce a clean 401, not a 500 that reveals a stack trace.
        """
        assert verify_password("anything", "not-a-bcrypt-hash") is False
        assert verify_password("anything", "") is False

    def test_hash_rejects_passwords_over_72_bytes(self):
        """
        bcrypt silently truncates at 72 bytes. Truncating instead of raising
        would mean two different long passwords authenticate interchangeably.
        """
        with pytest.raises(ValueError, match="72 characters or fewer"):
            hash_password("a" * 73)

    def test_the_limit_is_bytes_not_characters(self):
        """
        A 25-character CJK password is 75 UTF-8 bytes and must be rejected, even
        though it is well under 72 characters. Worth pinning: the check reads
        len(encoded), and someone "simplifying" it to len(plain) would introduce
        a silent-truncation bug that only affects non-ASCII passwords.
        """
        assert len("必" * 25) == 25
        assert len(("必" * 25).encode("utf-8")) == 75

        with pytest.raises(ValueError):
            hash_password("必" * 25)


# ---------------------------------------------------------------------------
# Pure logic: JWT encode / decode (zero doubles)
# ---------------------------------------------------------------------------
class TestAccessTokens:
    def test_round_trip_returns_the_subject(self):
        token = create_access_token(subject="user-123")
        assert decode_access_token(token) == "user-123"

    def test_token_carries_expiry_and_issued_at(self):
        token = create_access_token(subject="user-123")
        s = get_settings()
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
        assert "exp" in payload
        assert "iat" in payload
        assert payload["exp"] > payload["iat"]

    def test_expired_token_raises_expired_signature_error(self):
        token = _make_token({"sub": "user-123", "exp": datetime.now(UTC) - timedelta(minutes=1)})
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_access_token(token)

    def test_tampered_signature_raises_invalid_token_error(self):
        token = create_access_token(subject="user-123")
        tampered = token[:-4] + ("aaaa" if not token.endswith("aaaa") else "bbbb")
        with pytest.raises(jwt.InvalidTokenError):
            decode_access_token(tampered)

    def test_token_signed_with_the_wrong_key_is_rejected(self):
        s = get_settings()
        foreign = jwt.encode(
            {"sub": "user-123", "exp": datetime.now(UTC) + timedelta(minutes=5)},
            "a-completely-different-secret",
            algorithm=s.jwt_algorithm,
        )
        with pytest.raises(jwt.InvalidTokenError):
            decode_access_token(foreign)

    def test_token_without_a_sub_claim_is_rejected(self):
        """Covers the explicit `raise jwt.InvalidTokenError` in decode_access_token."""
        token = _make_token({"exp": datetime.now(UTC) + timedelta(minutes=5)})
        with pytest.raises(jwt.InvalidTokenError, match="sub"):
            decode_access_token(token)


class TestRememberMeTokenLifetime:
    """
    Behaviour change N2.

    REQUIRES the remember_me fix: `remember_me: bool` on LoginRequest,
    `create_access_token(subject, *, remember_me=...)`, and
    `remember_me_expire_minutes` in Settings.

    If that change is not applied, these fail with a TypeError on the keyword
    argument, which is the intended signal rather than a mysterious assertion.

    Before the fix the LoginPage checkbox was wired all the way to the request
    body as `rememberMe`, which LoginRequest did not declare, so Pydantic
    discarded it silently — and create_access_token had no expiry parameter to
    honour it anyway.
    """

    def test_remember_me_produces_a_longer_lived_token(self):
        s = get_settings()
        standard = jwt.decode(
            create_access_token(subject="u1"), s.jwt_secret, algorithms=[s.jwt_algorithm]
        )
        remembered = jwt.decode(
            create_access_token(subject="u1", remember_me=True),
            s.jwt_secret,
            algorithms=[s.jwt_algorithm],
        )
        assert (
            remembered["exp"] > standard["exp"]
        ), "remember_me must extend the token lifetime, not just be accepted"

    def test_login_request_accepts_remember_me(self):
        body = LoginRequest(email="a@b.com", password="password123", remember_me=True)
        assert body.remember_me is True

    def test_remember_me_defaults_to_false(self):
        body = LoginRequest(email="a@b.com", password="password123")
        assert body.remember_me is False


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------
class TestRegisterRequestValidation:
    def test_accepts_a_reasonable_password(self):
        body = RegisterRequest(email="new@example.com", password="password123")
        assert body.password == "password123"

    def test_rejects_a_password_under_8_characters(self):
        with pytest.raises(ValidationError, match="at least 8 characters"):
            RegisterRequest(email="new@example.com", password="short")

    def test_rejects_a_password_over_72_bytes(self):
        with pytest.raises(ValidationError, match="72 characters or fewer"):
            RegisterRequest(email="new@example.com", password="a" * 73)

    def test_rejects_a_malformed_email(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="not-an-email", password="password123")

    def test_length_floor_counts_characters_but_ceiling_counts_bytes(self):
        """
        Documents a real asymmetry in password_strength(): the >72 check uses
        UTF-8 bytes while the <8 check uses characters. A 4-character emoji
        password is 16 bytes, so it passes the byte ceiling and is correctly
        rejected by the character floor.
        """
        with pytest.raises(ValidationError, match="at least 8 characters"):
            RegisterRequest(email="new@example.com", password="🔑🔑🔑🔑")


# ---------------------------------------------------------------------------
# HTTP surface: /api/auth/*
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestRegister:
    async def test_register_returns_a_usable_token(self, client):
        resp = await client.post(
            "/api/auth/register",
            json={"email": "brand.new@example.com", "password": "password123"},
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["token_type"] == "bearer"
        assert decode_access_token(body["access_token"])

    async def test_duplicate_email_returns_409(self, client, tenant_user):
        resp = await client.post(
            "/api/auth/register",
            json={"email": tenant_user.email, "password": "password123"},
        )

        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    async def test_weak_password_returns_422(self, client):
        resp = await client.post(
            "/api/auth/register",
            json={"email": "weak@example.com", "password": "abc"},
        )
        assert resp.status_code == 422

    async def test_registered_user_can_immediately_log_in(self, client):
        await client.post(
            "/api/auth/register",
            json={"email": "immediate@example.com", "password": "password123"},
        )

        resp = await client.post(
            "/api/auth/login",
            json={"email": "immediate@example.com", "password": "password123"},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestLogin:
    async def test_correct_credentials_return_a_token(self, client, db):
        await _make_user(
            db,
            user_id="a1111111-1111-4111-8111-11111111111a",
            email="login.ok@example.com",
            password="password123",
        )

        resp = await client.post(
            "/api/auth/login",
            json={"email": "login.ok@example.com", "password": "password123"},
        )

        assert resp.status_code == 200
        assert decode_access_token(resp.json()["access_token"])

    async def test_wrong_password_returns_401(self, client, db):
        await _make_user(
            db,
            user_id="b2222222-2222-4222-8222-22222222222b",
            email="login.bad@example.com",
            password="password123",
        )

        resp = await client.post(
            "/api/auth/login",
            json={"email": "login.bad@example.com", "password": "wrong-password"},
        )
        assert resp.status_code == 401

    async def test_unknown_email_is_indistinguishable_from_a_wrong_password(self, client, db):
        """
        No user enumeration. Both cases must return the same status AND the same
        body, or an attacker can discover which addresses are registered.
        """
        await _make_user(
            db,
            user_id="c3333333-3333-4333-8333-33333333333c",
            email="exists@example.com",
            password="password123",
        )

        wrong_password = await client.post(
            "/api/auth/login",
            json={"email": "exists@example.com", "password": "wrong-password"},
        )
        unknown_email = await client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )

        assert wrong_password.status_code == unknown_email.status_code == 401
        assert wrong_password.json() == unknown_email.json()

    async def test_deactivated_account_returns_403(self, client, db):
        await _make_user(
            db,
            user_id="d4444444-4444-4444-8444-44444444444d",
            email="deactivated@example.com",
            password="password123",
            is_active=False,
        )

        resp = await client.post(
            "/api/auth/login",
            json={"email": "deactivated@example.com", "password": "password123"},
        )

        assert resp.status_code == 403
        assert "deactivated" in resp.json()["detail"].lower()


@pytest.mark.asyncio
class TestCurrentUserDependency:
    """
    get_current_user is where every protected route's security actually lives, and
    it was the least-covered module in the codebase. /api/auth/me is the smallest
    endpoint that exercises it end to end.
    """

    async def test_valid_token_returns_the_user(self, authed_client, tenant_user):
        resp = await authed_client.get("/api/auth/me")

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == tenant_user.id
        assert body["email"] == tenant_user.email
        assert body["is_active"] is True

    async def test_no_credentials_are_rejected(self, anon_client):
        resp = await anon_client.get("/api/auth/me")
        # 401 on this FastAPI version.
        #
        # I predicted 403 here and was wrong. HTTPBearer(auto_error=True) DID
        # raise 403 "Not authenticated" in older FastAPI releases; current
        # versions raise 401 with a WWW-Authenticate header, which is the
        # correct code for "no credentials supplied" per RFC 7235. Either way
        # the rejection happens in the security scheme, before
        # get_current_user's body runs.
        assert resp.status_code == 401

    async def test_malformed_token_returns_401(self, anon_client):
        resp = await anon_client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
        assert resp.status_code == 401

    async def test_expired_token_says_so(self, anon_client, tenant_user):
        expired = _make_token(
            {"sub": tenant_user.id, "exp": datetime.now(UTC) - timedelta(minutes=1)}
        )

        resp = await anon_client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})

        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    async def test_token_for_a_deleted_user_returns_401(self, anon_client):
        """
        A structurally valid, correctly signed token whose subject no longer
        exists. Covers the `if user is None` branch — the path that matters if an
        account is removed while a token is still in the wild.
        """
        orphan = create_access_token(subject="f9999999-9999-4999-8999-99999999999f")

        resp = await anon_client.get("/api/auth/me", headers={"Authorization": f"Bearer {orphan}"})
        assert resp.status_code == 401

    async def test_token_for_a_deactivated_user_returns_403(self, anon_client, db):
        """A valid token must stop working once the account is disabled."""
        user = await _make_user(
            db,
            user_id="e5555555-5555-4555-8555-55555555555e",
            email="disabled.later@example.com",
            password="password123",
            is_active=False,
        )

        token = create_access_token(subject=user.id)

        resp = await anon_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 403
        assert "deactivated" in resp.json()["detail"].lower()


@pytest.mark.asyncio
class TestProtectedRoutesRequireAuth:
    """
    The `client` fixture overrides get_db_for_user wholesale, which bypasses
    get_current_user — deliberately, so endpoint behaviour can be tested without
    tokens. The consequence is that nothing verified protected routes are
    actually protected. anon_client closes that hole.
    """

    @pytest.mark.parametrize(
        "method,path",
        [
            ("get", "/api/contacts"),
            ("get", "/api/tasks"),
            ("get", "/api/search?q=anything"),
            ("post", "/api/input/text"),
        ],
    )
    async def test_protected_route_rejects_anonymous_requests(self, anon_client, method, path):
        resp = await getattr(anon_client, method)(path)
        assert resp.status_code in (
            401,
            403,
        ), f"{method.upper()} {path} must not be reachable without credentials"

    async def test_health_endpoints_stay_public(self, anon_client):
        """Liveness and readiness probes must not require a token."""
        assert (await anon_client.get("/health")).status_code == 200
        assert (await anon_client.get("/ready")).status_code == 200
