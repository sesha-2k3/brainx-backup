"""
Root test configuration.

Test philosophy (aligned with your TDD principles):
─────────────────────────────────────────────────────
• "Unit" = a behavior, not a function or class.
  e.g. "creating a contact deduplicates by email" is one unit.

• Test doubles usage:
  - FAKE:  async SQLite database (real SQL, in-memory, fast)
  - STUB:  Groq API returns canned responses (no network)
  - DUMMY: placeholder values for required but irrelevant params
  - SPY:   verify that the Groq client was called (when relevant)
  - MOCK:  reserved ONLY for verifying foreign system interactions

• Tests should NOT break when you refactor internals.
  We test through public boundaries: HTTP endpoints, query functions,
  service functions — never patch private helpers.

Layers:
  tests/test_utils/    → Pure logic. Zero doubles.
  tests/test_domain/   → DB behaviors via query layer. Fake SQLite DB.
  tests/test_services/ → Service layer. Fake DB + Groq stubs.
  tests/test_api/      → HTTP endpoints. TestClient + Fake DB + Groq stubs.
"""

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.types import JSON

from src.db.database import Base


# ---------------------------------------------------------------------------
# SQLite compatibility: map PostgreSQL-specific types to SQLite equivalents
# ---------------------------------------------------------------------------
# JSONB doesn't exist in SQLite. We tell SQLAlchemy to compile it as JSON
# (which SQLite stores as TEXT). This lets us use the same ORM models in
# tests without maintaining a separate model layer.

@event.listens_for(Base.metadata, "before_create")
def _remap_jsonb_for_sqlite(target, connection, **kw):
    """Swap JSONB → JSON before table creation on SQLite."""
    if connection.dialect.name == "sqlite":
        for table in target.tables.values():
            for column in table.columns:
                if isinstance(column.type, JSONB):
                    column.type = JSON()


# ---------------------------------------------------------------------------
# Event loop: use a single loop for the entire test session
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# FAKE: Async SQLite database (real SQL engine, zero network, ephemeral)
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """Session-scoped async SQLite engine. Tables created once."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Per-test database session with automatic rollback.
    Each test gets a clean slate — no test pollution.
    """
    session_factory = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        # Start a nested transaction so we can roll back after each test
        async with session.begin():
            yield session
            # Rollback everything the test did
            await session.rollback()


# ---------------------------------------------------------------------------
# STUB: Groq client that returns canned responses (no network calls)
# ---------------------------------------------------------------------------
@pytest.fixture
def groq_stub():
    """
    A stub Groq client that returns predictable extraction results.
    Use this when testing code that calls the Groq API.
    """
    client = AsyncMock()

    # Default: chat completion returns valid JSON
    completion_response = MagicMock()
    completion_response.choices = [
        MagicMock(
            message=MagicMock(
                content='{"name": "Jane Doe", "email": "jane@example.com", '
                '"company": "Acme Corp", "role": "CTO", "category": "client", '
                '"context": "Met at conference", '
                '"interaction_summary": "Discussed partnership", '
                '"tasks": [{"title": "Send proposal", "due_date": "next week"}]}'
            )
        )
    ]
    client.chat.completions.create = AsyncMock(return_value=completion_response)

    # Default: audio transcription returns text
    transcription_response = MagicMock()
    transcription_response.text = "Met Jane Doe from Acme Corp, she is the CTO."
    transcription_response.duration = 15.0
    transcription_response.language = "en"
    client.audio.transcriptions.create = AsyncMock(return_value=transcription_response)

    return client


# ---------------------------------------------------------------------------
# Constants: dummy values for required but irrelevant params
# ---------------------------------------------------------------------------
TENANT_ID = "test-tenant"
