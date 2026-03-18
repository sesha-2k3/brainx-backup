"""
Root test configuration.
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC
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

from src.db.database import Base, TenantSession

# ---------------------------------------------------------------------------
# SQLite compatibility: map PostgreSQL-specific types to SQLite equivalents
# ---------------------------------------------------------------------------


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
TENANT_ID = "test-tenant"


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
    Uses TenantSession for auto-filter and auto-stamp.
    """
    session_factory = async_sessionmaker(
        async_engine,
        class_=TenantSession,
        expire_on_commit=False,
        tenant_id=TENANT_ID,
    )
    async with session_factory() as session, session.begin():
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# STUB: Groq client that returns canned responses (no network calls)
# ---------------------------------------------------------------------------
@pytest.fixture
def groq_stub():
    """
    A stub Groq client that returns predictable extraction results.
    """
    client = AsyncMock()

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

    transcription_response = MagicMock()
    transcription_response.text = "Met Jane Doe from Acme Corp, she is the CTO."
    transcription_response.duration = 15.0
    transcription_response.language = "en"
    client.audio.transcriptions.create = AsyncMock(return_value=transcription_response)

    return client


# ---------------------------------------------------------------------------
# Factory fixtures: create real ORM objects in the fake DB
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def make_contact(db):
    """Factory fixture: creates a contact with sensible defaults."""
    from src.db.queries import contacts as contact_queries

    async def _make(
        name="Test Contact",
        email=None,
        phone=None,
        company=None,
        role=None,
        category=None,
        context=None,
        notes=None,
    ):
        return await contact_queries.create_contact(
            db,
            name=name,
            email=email,
            phone=phone,
            company=company,
            role=role,
            category=category,
            context=context,
            notes=notes,
        )

    return _make


@pytest_asyncio.fixture
async def make_interaction(db):
    """Factory fixture: creates an interaction for a contact."""
    from datetime import datetime

    from src.db.queries import interactions as interaction_queries

    async def _make(
        contact_id,
        summary="Test interaction",
        interaction_type="note",
        occurred_at=None,
    ):
        return await interaction_queries.create_interaction(
            db,
            contact_id=contact_id,
            interaction_type=interaction_type,
            summary=summary,
            occurred_at=occurred_at or datetime.now(UTC),
        )

    return _make


@pytest_asyncio.fixture
async def make_task(db):
    """Factory fixture: creates a task."""
    from src.db.queries import tasks as task_queries

    async def _make(
        title="Test task",
        contact_id=None,
        due_date=None,
        description=None,
    ):
        return await task_queries.create_task(
            db,
            title=title,
            contact_id=contact_id,
            due_date=due_date,
            description=description,
        )

    return _make
