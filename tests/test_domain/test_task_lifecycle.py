"""
Test: Task lifecycle behaviors.

Behaviors:
  - "creating a task stores it as pending"
  - "completing a task sets timestamp and status"
  - "cancelling a task changes status"
  - "listing tasks filters by status and contact"
  - "tasks due by a date are retrievable"
  - "reminder tracking works correctly"
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.db.models import TaskStatus
from src.db.queries import tasks as task_queries
from tests.conftest import TENANT_ID


@pytest.mark.asyncio
class TestTaskCreation:
    async def test_create_pending(self, db, make_task):
        task = await make_task(title="Send invoice")
        assert task.status == TaskStatus.PENDING
        assert task.title == "Send invoice"

    async def test_create_with_contact(self, db, make_contact, make_task):
        contact = await make_contact(name="Task Owner")
        task = await make_task(title="Call back", contact_id=contact.id)
        assert task.contact_id == contact.id

    async def test_create_with_due_date(self, db, make_task):
        due = datetime(2025, 12, 31, tzinfo=UTC)
        task = await make_task(title="Year end review", due_date=due)
        assert task.due_date == due


@pytest.mark.asyncio
class TestTaskCompletion:
    async def test_complete_sets_status_and_timestamp(self, db, make_task):
        task = await make_task(title="Finish report")
        completed = await task_queries.complete_task(db, task.id, TENANT_ID)

        assert completed.status == TaskStatus.COMPLETED
        assert completed.completed_at is not None

    async def test_complete_nonexistent_returns_none(self, db):
        result = await task_queries.complete_task(db, "fake-id", TENANT_ID)
        assert result is None


@pytest.mark.asyncio
class TestTaskCancellation:
    async def test_cancel_changes_status(self, db, make_task):
        task = await make_task(title="Cancelled task")
        cancelled = await task_queries.cancel_task(db, task.id, TENANT_ID)
        assert cancelled.status == TaskStatus.CANCELLED

    async def test_cancel_nonexistent_returns_none(self, db):
        result = await task_queries.cancel_task(db, "nope", TENANT_ID)
        assert result is None


@pytest.mark.asyncio
class TestTaskListing:
    async def test_list_pending_only(self, db, make_task):
        await make_task(title="Active")
        t2 = await make_task(title="Done")
        await task_queries.complete_task(db, t2.id, TENANT_ID)

        pending = await task_queries.list_pending_tasks(db, TENANT_ID)
        titles = [t.title for t in pending]
        assert "Active" in titles
        assert "Done" not in titles

    async def test_list_by_contact(self, db, make_contact, make_task):
        c1 = await make_contact(name="Contact A")
        c2 = await make_contact(name="Contact B")
        await make_task(title="Task for A", contact_id=c1.id)
        await make_task(title="Task for B", contact_id=c2.id)

        tasks = await task_queries.list_tasks_for_contact(db, c1.id, TENANT_ID)
        assert all(t.contact_id == c1.id for t in tasks)


@pytest.mark.asyncio
class TestTasksDueBy:
    async def test_finds_overdue_tasks(self, db, make_task):
        past = datetime.now(UTC) - timedelta(days=1)
        future = datetime.now(UTC) + timedelta(days=7)

        await make_task(title="Overdue", due_date=past)
        await make_task(title="Future", due_date=future)

        now = datetime.now(UTC)
        due = await task_queries.list_tasks_due_by(db, now, TENANT_ID)
        titles = [t.title for t in due]
        assert "Overdue" in titles
        assert "Future" not in titles


@pytest.mark.asyncio
class TestTaskReminders:
    async def test_due_reminders_found(self, db):
        past_reminder = datetime.now(UTC) - timedelta(hours=1)
        task = await task_queries.create_task(
            db,
            title="Remind me",
            reminder_at=past_reminder,
            tenant_id=TENANT_ID,
        )

        now = datetime.now(UTC)
        reminders = await task_queries.get_due_reminders(db, now, TENANT_ID)
        assert any(t.id == task.id for t in reminders)

    async def test_mark_reminder_sent(self, db):
        task = await task_queries.create_task(
            db,
            title="Sent reminder",
            reminder_at=datetime.now(UTC) - timedelta(hours=1),
            tenant_id=TENANT_ID,
        )

        marked = await task_queries.mark_reminder_sent(db, task.id, TENANT_ID)
        assert marked.reminder_sent is True


@pytest.mark.asyncio
class TestTaskUpdate:
    async def test_update_title(self, db, make_task):
        task = await make_task(title="Old title")
        updated = await task_queries.update_task(db, task.id, TENANT_ID, title="New title")
        assert updated.title == "New title"

    async def test_update_nonexistent_returns_none(self, db):
        result = await task_queries.update_task(db, "nope", TENANT_ID, title="Ghost")
        assert result is None
