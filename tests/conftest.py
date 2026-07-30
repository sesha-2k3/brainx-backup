"""
Root test configuration.

Testing approach (Inside-Out / classicist for the domain, Outside-In only at
foreign boundaries):

  - The database is a REAL SQL engine, not a mock. Query functions, the
    TenantSession auto-filter, and cascade behaviour are all exercised for real.
  - Only genuinely foreign systems are doubled: the Groq API (network) and the
    Tesseract binary (subprocess).
  - Pure functions (utils/*) get no doubles at all.

The guiding constraint: a fake must not be MORE PERMISSIVE than production. A
suite that passes on data Postgres would reject is worse than no suite, because
it produces confidence rather than information.
"""

import json
import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

# ---------------------------------------------------------------------------
# Environment must be set BEFORE any `src` import. This block is load-bearing
# and its position is not stylistic.
#
# Settings declares `database_url: str` and `groq_api_key: str` with no
# defaults, and src/db/database.py, src/main.py and src/auth/service.py each run
# `settings = get_settings()` at MODULE level. So the very first `from src...`
# import instantiates Settings, and without these values it raises
# pydantic_core.ValidationError before a single test is collected.
#
# It currently works on a developer machine only because a .env file happens to
# be present. CI has no .env, so the suite would fail at import there while
# passing locally. setdefault() means a real .env still wins if one exists.
#
# A dependency-injection override cannot fix this: the module-level call has
# already happened by the time FastAPI resolves anything.
# ---------------------------------------------------------------------------
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("GROQ_API_KEY", "test-fake-key")
# 32+ bytes: PyJWT emits InsecureKeyLengthWarning below the RFC 7518 minimum
# for SHA-256, which produced 25 warnings per auth run.
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production-0123456789abcdef")
os.environ.setdefault("APP_ENV", "testing")

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.types import JSON, String

from src.db.database import Base, TenantSession
from src.db.models import User

# ---------------------------------------------------------------------------
# SQLite compatibility: map PostgreSQL-specific types to SQLite equivalents
#
# NOTE: this mutates Base.metadata in place — the same global object the
# application imports. It is survivable because tests never touch Postgres in
# the same process, but it is test code reaching into production schema
# definitions, and it is irreversible once it fires.
#
# The cleaner fix is to move the compatibility into models.py so it needs no
# test-time hook at all:
#
#     extracted_data: Mapped[dict] = mapped_column(
#         JSONB().with_variant(JSON(), "sqlite"), nullable=False
#     )
#
# Until that lands, this hook stays.
# ---------------------------------------------------------------------------


@event.listens_for(Base.metadata, "before_create")
def _remap_pg_types_for_sqlite(target, connection, **kw):
    """
    Swap PostgreSQL-only column types for SQLite equivalents before CREATE TABLE.

    JSONB -> JSON is the obvious one: JSONB has no SQLite compiler at all, so
    create_all() fails outright without this.

    UUID -> String(32) is subtler and produced a genuinely baffling failure.
    SQLAlchemy renders postgresql.UUID as the column type "UUID" on SQLite, and
    SQLite assigns affinity by substring: INT, CHAR, CLOB, TEXT, BLOB, REAL,
    FLOA, DOUB. "UUID" matches none of them, so the column gets NUMERIC affinity.

    Meanwhile the Uuid type's bind processor stores the hex form with hyphens
    stripped — 32 characters. If that hex happens to be all digits, it is a
    well-formed integer literal, and NUMERIC affinity converts it. 32 digits
    overflows int64, so SQLite promotes it to REAL:

        "11111111-1111-4111-8111-111111111111"
          -> stored as "11111111111141118111111111111111"
          -> read back as 1.1111111111141117e+31

    The read then explodes inside the Uuid RESULT processor:

        value = str(_python_UUID(value))
        AttributeError: 'float' object has no attribute 'replace'

    ...several frames deep inside an unrelated request handler, with nothing
    pointing at the id that caused it.

    The trap is that it only fires for UUIDs whose hex is entirely numeric.
    A real uuid4 almost always contains a hex letter, so it stays TEXT and works
    — which is why the suite passed for months and only broke on hand-written
    ids like "11111111-1111-...". Forcing TEXT affinity removes the whole class.
    """
    if connection.dialect.name != "sqlite":
        return

    for table in target.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
            elif isinstance(column.type, UUID):
                column.type = String(32)


# ---------------------------------------------------------------------------
# NOTE: there is deliberately no `event_loop` fixture here.
#
# Overriding event_loop was deprecated in pytest-asyncio 0.23 and removed in
# 1.0, and pyproject pins pytest-asyncio>=0.23.0 — so a fresh resolve gets a
# version where the override either warns loudly or stops working.
#
# It also interacted badly with the session-scoped `async_engine` fixture: from
# 0.23 onward, async fixtures default to a FUNCTION-scoped loop, so a
# session-scoped async fixture is created on one loop while the tests consuming
# it run on another, producing:
#
#     RuntimeError: Task ... got Future ... attached to a different loop
#
# The replacement is configuration, not a fixture. Add to pyproject.toml:
#
#     [tool.pytest.ini_options]
#     asyncio_mode = "auto"
#     asyncio_default_fixture_loop_scope = "session"
#
# (or decorate individual fixtures with @pytest_asyncio.fixture(loop_scope=...)).
# ---------------------------------------------------------------------------

# A real UUID, because Contact.tenant_id is UUID(as_uuid=False) with a foreign
# key to users.id. The previous literal "test-tenant" was neither a UUID nor a
# row that existed — it only worked because SQLite disables foreign keys by
# default. On Postgres every insert in the suite would have failed the FK.
TENANT_ID = str(uuid4())
TEST_USER_EMAIL = "test-user@example.com"


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """Session-scoped async SQLite engine. Tables created once."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # SQLite ships with foreign key enforcement OFF. Leaving it off makes the
    # fake more permissive than production in two ways that matter here:
    #   1. tenant_id values with no matching users row are accepted.
    #   2. ON DELETE CASCADE / SET NULL never fire, so the cascade behaviour
    #      that delete_contact now relies on is not actually exercised.
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fks(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def tenant_user(async_engine):
    """
    The User row that TENANT_ID refers to.

    Required now that foreign keys are enforced: tenant_id is an FK to users.id,
    so every Contact/Interaction/Task/Proposal insert needs this row to exist.
    Created unscoped, since User itself is not tenant-scoped.
    """
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with factory() as session:
        user = User(
            id=TENANT_ID,
            email=TEST_USER_EMAIL,
            hashed_password="not-a-real-hash",
        )
        session.add(user)
        await session.commit()
        return user


@pytest_asyncio.fixture
async def db(async_engine, tenant_user) -> AsyncGenerator[AsyncSession, None]:
    """
    Per-test tenant-scoped session, rolled back afterwards.

    Uses TenantSession so the auto-filter and auto-stamp behaviour is under test
    rather than bypassed.

    The previous version was `async with session_factory() as session,
    session.begin():` followed by an explicit rollback inside the block. That
    nests two transaction managers: the explicit rollback runs first, then
    session.begin().__aexit__ attempts to COMMIT the transaction that was just
    rolled back. Letting the session manage its own transaction is equivalent
    and has one owner.

    ISOLATION CAVEAT: this relies on nothing calling session.commit(). That
    holds today — query functions only flush, and commits happen in the
    get_db_for_user dependency, which tests override. If a test ever needs to
    exercise committing code, switch to binding the session to an outer
    connection-level transaction with join_transaction_mode="create_savepoint",
    which turns inner commits into savepoint releases. That also needs the
    documented pysqlite BEGIN workaround, which is why it is not the default
    here.
    """
    session_factory = async_sessionmaker(
        async_engine,
        class_=TenantSession,
        expire_on_commit=False,
        tenant_id=TENANT_ID,
    )
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


# ---------------------------------------------------------------------------
# STUB: Groq client that returns canned responses (no network calls)
# ---------------------------------------------------------------------------
CONTACT_EXTRACTION_JSON = {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "company": "Acme Corp",
    "role": "CTO",
    "category": "client",
    "context": "Met at conference",
    "interaction_summary": "Discussed partnership",
    "tasks": [{"title": "Send proposal", "due_date": "next week"}],
}


@pytest.fixture
def groq_stub():
    """
    A stub Groq client returning predictable results.

    The completion response is SETTABLE, because a single hardcoded payload
    cannot serve every caller: extract_contact_data() wants the contact shape
    above, while parse_query() and detect_intent() expect entirely different
    JSON. A fixed response silently feeds contact-extraction JSON to the query
    parser, which then either raises or produces a nonsense intent — and the
    test that "passes" tells you nothing about the parser.

    Usage:
        groq_stub.set_completion({"intent": "contact_lookup", "name": "Eddie"})
        groq_stub.set_completion_text("not valid json")   # error-path tests
    """
    client = AsyncMock()

    def _wrap(content: str) -> MagicMock:
        return MagicMock(choices=[MagicMock(message=MagicMock(content=content))])

    def set_completion(payload: dict) -> None:
        client.chat.completions.create = AsyncMock(return_value=_wrap(json.dumps(payload)))

    def set_completion_text(raw: str) -> None:
        client.chat.completions.create = AsyncMock(return_value=_wrap(raw))

    client.set_completion = set_completion
    client.set_completion_text = set_completion_text
    set_completion(CONTACT_EXTRACTION_JSON)

    transcription_response = MagicMock()
    transcription_response.text = "Met Jane Doe from Acme Corp, she is the CTO."
    transcription_response.duration = 15.0
    transcription_response.language = "en"
    client.audio.transcriptions.create = AsyncMock(return_value=transcription_response)

    return client


# ---------------------------------------------------------------------------
# Factory fixtures: create real ORM objects in the fake DB
#
# Defaults are intentionally minimal. Each factory accepts every column a test
# might assert on — including website and tags, which the previous versions
# omitted, making it impossible to write a test for website extraction or tag
# filtering without hand-rolling the insert.
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def make_contact(db):
    """Factory: creates a contact with sensible defaults."""
    from src.db.queries import contacts as contact_queries

    async def _make(
        name="Test Contact",
        email=None,
        phone=None,
        company=None,
        role=None,
        website=None,
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
            website=website,
            category=category,
            context=context,
            notes=notes,
        )

    return _make


@pytest_asyncio.fixture
async def make_interaction(db):
    """Factory: creates an interaction for a contact."""
    from src.db.queries import interactions as interaction_queries

    async def _make(
        contact_id,
        summary="Test interaction",
        interaction_type="note",
        occurred_at=None,
        raw_transcript=None,
    ):
        return await interaction_queries.create_interaction(
            db,
            contact_id=contact_id,
            interaction_type=interaction_type,
            summary=summary,
            occurred_at=occurred_at or datetime.now(UTC),
            raw_transcript=raw_transcript,
        )

    return _make


@pytest_asyncio.fixture
async def make_task(db):
    """Factory: creates a task."""
    from src.db.queries import tasks as task_queries

    async def _make(
        title="Test task",
        contact_id=None,
        due_date=None,
        description=None,
        reminder_at=None,
    ):
        return await task_queries.create_task(
            db,
            title=title,
            contact_id=contact_id,
            due_date=due_date,
            description=description,
            reminder_at=reminder_at,
        )

    return _make


@pytest.fixture
def frozen_now():
    """
    A fixed timezone-aware instant for date assertions.

    Aware on purpose: every DateTime column is timezone=True, and comparing a
    naive datetime against one raises TypeError. Tests that build naive
    datetimes will pass on SQLite and fail on Postgres.
    """
    return datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
