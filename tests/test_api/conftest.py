"""
API test fixtures.

The TestClient exercises the full HTTP stack (routing, validation, serialization)
but with FAKE dependencies injected:
  - Database → same in-memory SQLite from root conftest (auto-rollback per test)
  - Settings → patched at both DI level AND module level in web.py
  - Groq client → stub (no network)
  - Auth → bypassed: get_db_for_user yields the test DB directly,
    so no Bearer token is required in any test request.
"""

from unittest.mock import patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.config import Settings, get_settings
from src.db import get_db, get_db_for_user
from tests.conftest import TENANT_ID


# ---------------------------------------------------------------------------
# Test settings
# ---------------------------------------------------------------------------
def get_test_settings() -> Settings:
    """Return test settings without needing a .env file."""
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        groq_api_key="test-fake-key",
        app_env="testing",
        tenant_id=TENANT_ID,
    )


@pytest_asyncio.fixture
async def client(db):
    """
    Async HTTP test client with dependency overrides.

    Both get_db and get_db_for_user are overridden with the same per-test
    TenantSession, so:
      - All queries are scoped to TENANT_ID (same as before the auth refactor)
      - No Bearer token is needed — auth is fully bypassed in tests
    """
    from src.main import app

    async def override_get_db():
        yield db

    # Override both the old and new db dependencies with the same test session
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_for_user] = override_get_db
    app.dependency_overrides[get_settings] = get_test_settings

    test_settings = get_test_settings()
    with patch("src.api.web.settings", test_settings):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()
