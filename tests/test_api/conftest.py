"""
API test fixtures.

The TestClient exercises the full HTTP stack (routing, validation, serialization)
with FAKE dependencies injected:
  - Database  -> the same in-memory SQLite session from the root conftest
  - Groq      -> stub (no network)
  - Auth      -> bypassed in `client`, exercised for real in `authed_client`

Both DB dependencies are overridden. Overriding only the tenant-scoped one
leaves /ready pointing at whatever DATABASE_URL resolves to, i.e. a real
Postgres — see the note on get_db_unscoped below.
"""

from contextlib import ExitStack
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi import Depends
from httpx import ASGITransport, AsyncClient

from src.auth.dependencies import get_current_user
from src.auth.service import create_access_token
from src.config import Settings
from src.db import get_db_for_user, get_db_unscoped

# ---------------------------------------------------------------------------
# NOTE on what was removed here, and why each item was a failure:
#
# 1. `from src.db import get_db, get_db_for_user`
#    get_db no longer exists. It resolved tenant_id from settings.tenant_id,
#    defaulting to the literal "default" — impossible now that Contact.tenant_id
#    is a UUID FK to users.id. This import is the ImportError that stopped
#    collection entirely:
#        ImportError: cannot import name 'get_db' from 'src.db'
#
# 2. `app.dependency_overrides[get_db] = override_get_db`
#    Nothing to override. get_db_for_user is the only tenant-scoped session
#    dependency now.
#
# 3. `with patch("src.api.web.settings", test_settings)`
#    THIS WOULD HAVE BEEN THE NEXT ERROR. web.py's module-level
#    `settings = get_settings()` was deleted along with settings.tenant_id, and
#    mock.patch raises when the target attribute is absent:
#        AttributeError: <module 'src.api.web'> does not have the attribute 'settings'
#
# 4. `app.dependency_overrides[get_settings] = get_test_settings`
#    A no-op. get_settings is never used as a FastAPI dependency anywhere in the
#    codebase — verified by grep for `Depends(get_settings)`. Modules call
#    get_settings() directly at import time, which a DI override cannot reach.
#
# 5. `Settings(..., tenant_id=TENANT_ID)`
#    The tenant_id field was removed. SettingsConfigDict(extra="ignore") means
#    this is silently discarded rather than raising, which is worse: it reads as
#    though the test session's tenant is configured here when in fact TENANT_ID
#    reaches the session through the root conftest's session factory.
# ---------------------------------------------------------------------------


def get_test_settings() -> Settings:
    """
    Test settings without needing a .env file.

    Retained for direct use by tests that want a Settings object. It is NOT
    registered as a dependency override — see note 4 above.
    """
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        groq_api_key="test-fake-key",
        app_env="testing",
    )


@pytest_asyncio.fixture
async def client(db):
    """
    Async HTTP client with auth bypassed.

    Overriding get_db_for_user replaces the whole dependency, so its
    `current_user=Depends(get_current_user)` sub-dependency never executes and no
    Bearer token is required. Use this for testing endpoint BEHAVIOUR.

    Use `authed_client` when the thing under test is authentication itself.
    """
    from src.main import app

    async def override_get_db():
        yield db

    # get_db_unscoped must be overridden too. It is not merely unused-by-default:
    # /ready depends on it, and unoverridden it builds a session from the
    # module-level engine created from the real DATABASE_URL. That makes
    # test_ready_returns_connected either fail with 503 (no local Postgres) or
    # pass by talking to a real database (not hermetic). get_current_user also
    # depends on it, which matters for authed_client below.
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db_for_user] = override_get_db
    app.dependency_overrides[get_db_unscoped] = override_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        # Restore rather than clear(): clear() also discards overrides installed
        # by an enclosing fixture or by the test itself, which silently changes
        # behaviour depending on fixture ordering.
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest_asyncio.fixture
async def authed_client(db, tenant_user):
    """
    Async HTTP client that goes through REAL authentication.

    Nothing currently tests auth. `client` overrides get_db_for_user wholesale,
    which bypasses get_current_user, so token validation, the 401 paths, the
    deactivated-account 403, and the /api/auth/* endpoints have no coverage at
    all — and there is no test_auth.py in the suite.

    The trick that makes this work without touching the engine: a dependency
    override may declare its OWN dependencies, and FastAPI resolves them. So this
    override still runs get_current_user for real (meaning real JWT decoding and
    real 401s) while handing back the test session.

    Requests are pre-authenticated as the seeded tenant_user, so the token's
    subject matches TENANT_ID and the session's tenant scope agrees with the
    caller's identity — as it does in production.
    """
    from src.main import app

    async def override_get_db_unscoped():
        yield db

    async def override_get_db_for_user(current_user=Depends(get_current_user)):
        yield db

    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db_unscoped] = override_get_db_unscoped
    app.dependency_overrides[get_db_for_user] = override_get_db_for_user

    token = create_access_token(subject=tenant_user.id)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest_asyncio.fixture
async def anon_client(db):
    """
    Client with real auth and NO credentials, for asserting rejection.

    HTTPBearer is constructed with auto_error=True, so a request with no
    Authorization header is rejected by the security scheme before
    get_current_user runs — that path returns 403, not 401. Tests should assert
    the status they actually observe rather than the one that seems intuitive.
    """
    from src.main import app

    async def override_get_db_unscoped():
        yield db

    async def override_get_db_for_user(current_user=Depends(get_current_user)):
        yield db

    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db_unscoped] = override_get_db_unscoped
    app.dependency_overrides[get_db_for_user] = override_get_db_for_user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.fixture
def groq_patched(groq_stub):
    """
    Patch the Groq client factory so API-level tests never reach the network.

    groq_stub on its own only builds a double; something has to install it.
    Tests that post to /api/input/* need this, or extract_contact_data() will
    attempt a real API call with the fake key and fail on network rather than on
    anything the test is about.

    PATCH TARGET MATTERS. Four modules each do:

        from src.services.groq_client import get_groq_client

    A from-import binds the function object into the IMPORTING module's namespace
    at import time, so patching src.services.groq_client.get_groq_client rebinds
    a name nobody reads — the four callers keep their original reference and the
    real client is used anyway. The patch has to land on each use site.

    The existing unit tests already do this correctly with per-test decorators
    such as @patch("src.services.extraction.get_groq_client"). This fixture is
    the convenience version for API-level tests that traverse several of these
    modules in one request.
    """
    targets = [
        "src.services.extraction.get_groq_client",
        "src.services.query_parser.get_groq_client",
        "src.services.semantic_search.get_groq_client",
        "src.services.transcription.get_groq_client",
    ]
    with ExitStack() as stack:
        for target in targets:
            stack.enter_context(patch(target, return_value=groq_stub))
        yield groq_stub
