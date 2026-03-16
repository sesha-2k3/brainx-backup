"""
Domain test fixtures — helpers for creating test entities.

These are FACTORIES, not mocks. They create real ORM objects in the fake DB.
"""

import pytest_asyncio

from src.db.queries import contacts as contact_queries
from src.db.queries import interactions as interaction_queries
from src.db.queries import tasks as task_queries
from tests.conftest import TENANT_ID

from datetime import datetime, timezone


@pytest_asyncio.fixture
async def make_contact(db):
    """Factory fixture: creates a contact with sensible defaults."""

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
            tenant_id=TENANT_ID,
        )

    return _make


@pytest_asyncio.fixture
async def make_interaction(db):
    """Factory fixture: creates an interaction for a contact."""

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
            occurred_at=occurred_at or datetime.now(timezone.utc),
            tenant_id=TENANT_ID,
        )

    return _make


@pytest_asyncio.fixture
async def make_task(db):
    """Factory fixture: creates a task."""

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
            tenant_id=TENANT_ID,
        )

    return _make
