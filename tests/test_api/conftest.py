"""
API test fixtures.

The TestClient exercises the full HTTP stack (routing, validation, serialization)
but with FAKE dependencies injected via FastAPI's dependency_overrides:
  - Database → same in-memory SQLite from conftest
  - Settings → test settings (no real env vars needed)
  - Groq client → stub (no network)

This is an integration test through the HTTP boundary,
NOT a unit test of individual endpoint functions.
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock

from httpx import AsyncClient, ASGITransport

from src.db import get_db
from src.config import get_settings, Settings


# ---------------------------------------------------------------------------
# Test settings: no real env vars, no real Groq key
# ---------------------------------------------------------------------------
def get_test_settings() -> Settings:
    """Return test settings without needing a .env file."""
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        groq_api_key="test-fake-key",
        app_env="testing",
        tenant_id="test-tenant",
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up overrides
    app.dependency_overrides.clear()
