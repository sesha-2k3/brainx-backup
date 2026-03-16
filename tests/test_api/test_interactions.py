"""
Test: Interaction CRUD via HTTP API.

Behaviors:
  - "POST /api/interactions creates an interaction for an existing contact"
  - "POST /api/interactions returns 404 for nonexistent contact"
  - "PATCH /api/interactions/{id} updates fields"
  - "DELETE /api/interactions/{id} removes interaction"
"""

import pytest


@pytest.mark.asyncio
class TestCreateInteraction:
    async def test_create_for_existing_contact(self, client, db, make_contact):
        contact = await make_contact(name="Interaction Target")
        resp = await client.post(
            "/api/interactions",
            json={
                "contact_id": contact.id,
                "interaction_type": "meeting",
                "summary": "Lunch meeting to discuss Q3 plans",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["interaction"]["summary"] == "Lunch meeting to discuss Q3 plans"

    async def test_create_with_custom_date(self, client, db, make_contact):
        contact = await make_contact(name="Date Target")
        resp = await client.post(
            "/api/interactions",
            json={
                "contact_id": contact.id,
                "summary": "Past meeting",
                "occurred_at": "2025-01-15T10:00:00+00:00",
            },
        )
        assert resp.status_code == 200

    async def test_create_for_nonexistent_contact_returns_404(self, client):
        resp = await client.post(
            "/api/interactions",
            json={
                "contact_id": "nonexistent-uuid",
                "summary": "Ghost meeting",
            },
        )
        assert resp.status_code == 404

    async def test_create_missing_summary_fails(self, client, db, make_contact):
        contact = await make_contact(name="No Summary")
        resp = await client.post(
            "/api/interactions",
            json={
                "contact_id": contact.id,
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestUpdateInteraction:
    async def test_update_summary(self, client, db, make_contact, make_interaction):
        contact = await make_contact(name="Update Int Target")
        interaction = await make_interaction(contact.id, summary="Original")

        resp = await client.patch(
            f"/api/interactions/{interaction.id}",
            json={"summary": "Updated summary"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_update_nonexistent_returns_404(self, client):
        resp = await client.patch(
            "/api/interactions/fake-id",
            json={"summary": "Ghost"},
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestDeleteInteraction:
    async def test_delete_existing(self, client, db, make_contact, make_interaction):
        contact = await make_contact(name="Delete Int Target")
        interaction = await make_interaction(contact.id, summary="To delete")

        resp = await client.delete(f"/api/interactions/{interaction.id}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_delete_nonexistent_returns_404(self, client):
        resp = await client.delete("/api/interactions/fake-id")
        assert resp.status_code == 404
