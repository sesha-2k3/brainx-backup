"""
API test fixtures.

The TestClient exercises the full HTTP stack (routing, validation, serialization)
but with FAKE dependencies injected:
  - Database → same in-memory SQLite from conftest
  - Settings → patched at both DI level AND module level in web.py
  - Groq client → stub (no network)

IMPORTANT: web.py captures `settings = get_settings()` at *module import time*.
FastAPI's dependency_overrides only affects Depends(get_settings) injections —
it does NOT touch that module-level variable. We must patch it explicitly.
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock

from httpx import AsyncClient, ASGITransport

from src.db import get_db
from src.config import get_settings, Settings
from tests.conftest import TENANT_ID


# ---------------------------------------------------------------------------
# Test settings: matches TENANT_ID from root conftest
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
    Uses the same per-test DB session (with rollback) from root conftest.
    """
    from src.main import app

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = get_test_settings

    # Patch the MODULE-LEVEL settings variable in web.py
    # so that settings.tenant_id matches our test TENANT_ID
    test_settings = get_test_settings()
    with patch("src.api.web.settings", test_settings):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    # Clean up overrides
    app.dependency_overrides.clear()
