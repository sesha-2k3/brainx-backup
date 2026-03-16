"""
Test: Task CRUD via HTTP API.

Behaviors:
  - "POST /api/tasks creates a task"
  - "GET /api/tasks lists pending tasks"
  - "PATCH /api/tasks/{id} updates task fields"
  - "POST /api/tasks/{id}/complete marks as completed"
  - "DELETE /api/tasks/{id} cancels a task"
  - "nonexistent task returns 404 for all operations"
"""

import pytest

from tests.conftest import TENANT_ID


@pytest.mark.asyncio
class TestCreateTask:

    async def test_create_basic(self, client):
        resp = await client.post("/api/tasks", json={
            "title": "API Task",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["task"]["title"] == "API Task"
        assert "id" in body["task"]

    async def test_create_with_contact(self, client, db, make_contact):
        contact = await make_contact(name="Task Owner")
        resp = await client.post("/api/tasks", json={
            "title": "Call back",
            "contact_id": contact.id,
        })
        assert resp.status_code == 200

    async def test_create_missing_title_fails(self, client):
        resp = await client.post("/api/tasks", json={
            "description": "No title provided",
        })
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestListTasks:

    async def test_list_returns_array(self, client, db, make_task):
        await make_task(title="Visible Task")
        resp = await client.get("/api/tasks")
        assert resp.status_code == 200
        assert "tasks" in resp.json()

    async def test_list_by_contact(self, client, db, make_contact, make_task):
        contact = await make_contact(name="Filter Target")
        await make_task(title="Scoped Task", contact_id=contact.id)
        await make_task(title="Other Task")

        resp = await client.get(f"/api/tasks?contact_id={contact.id}")
        assert resp.status_code == 200
        tasks = resp.json()["tasks"]
        assert all(t["contact_id"] == contact.id for t in tasks)


@pytest.mark.asyncio
class TestUpdateTask:

    async def test_update_title(self, client, db, make_task):
        task = await make_task(title="Old Title")
        resp = await client.patch(
            f"/api/tasks/{task.id}",
            json={"title": "New Title"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_update_due_date_relative(self, client, db, make_task):
        task = await make_task(title="Due Task")
        resp = await client.patch(
            f"/api/tasks/{task.id}",
            json={"due_date": "tomorrow"},
        )
        assert resp.status_code == 200

    async def test_clear_due_date(self, client, db, make_task):
        task = await make_task(title="Clear Due")
        resp = await client.patch(
            f"/api/tasks/{task.id}",
            json={"due_date": ""},
        )
        assert resp.status_code == 200

    async def test_update_nonexistent_returns_404(self, client):
        resp = await client.patch(
            "/api/tasks/fake-id",
            json={"title": "Ghost"},
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestCompleteTask:

    async def test_complete(self, client, db, make_task):
        task = await make_task(title="Complete Me")
        resp = await client.post(f"/api/tasks/{task.id}/complete")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_complete_nonexistent_returns_404(self, client):
        resp = await client.post("/api/tasks/fake-id/complete")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestDeleteTask:

    async def test_delete(self, client, db, make_task):
        task = await make_task(title="Delete Me")
        resp = await client.delete(f"/api/tasks/{task.id}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_delete_nonexistent_returns_404(self, client):
        resp = await client.delete("/api/tasks/fake-id")
        assert resp.status_code == 404
