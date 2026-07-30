"""
Test: Contact CRUD via HTTP API.

Behaviors:
  - "POST /api/contacts creates a contact and returns id"
  - "GET /api/contacts lists contacts"
  - "GET /api/contacts/{id} returns contact with interactions"
  - "PATCH /api/contacts/{id} updates fields"
  - "DELETE /api/contacts/{id} removes contact and related data"
  - "GET /api/contacts?category=investor filters correctly"
  - "GET /api/contacts/{id} returns 404 for nonexistent"
  - "POST /api/contacts/{id}/set-reminder configures reminders"
  - "POST /api/contacts/{id}/mark-contacted resets reminder"
"""

import pytest

# A syntactically valid UUID that is deliberately never inserted.
#
# The 404 tests below previously used "nonexistent-uuid" / "fake-id", which are
# not UUIDs at all. Now that contact_id path params are constrained to a UUID
# shape, those strings are rejected as 422 before any lookup happens — so the
# tests were asserting "absent contact" while actually exercising "malformed id".
# Two different behaviours, one assertion. They are separated below.
ABSENT_CONTACT_ID = "00000000-0000-4000-8000-000000000000"
MALFORMED_CONTACT_ID = "not-a-uuid"


@pytest.mark.asyncio
class TestCreateContact:
    async def test_create_returns_success(self, client):
        resp = await client.post(
            "/api/contacts",
            json={
                "name": "API Alice",
                "email": "api-alice@example.com",
                "company": "APICorp",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["contact"]["name"] == "API Alice"
        assert "id" in body["contact"]

    async def test_create_minimal(self, client):
        resp = await client.post("/api/contacts", json={"name": "Just A Name"})
        assert resp.status_code == 200

    async def test_create_missing_name_fails(self, client):
        resp = await client.post("/api/contacts", json={"email": "no-name@test.com"})
        assert resp.status_code == 422  # Pydantic validation


@pytest.mark.asyncio
class TestListContacts:
    async def test_list_returns_array(self, client, db, make_contact):
        await make_contact(name="Listed Person")
        resp = await client.get("/api/contacts")
        assert resp.status_code == 200
        assert "contacts" in resp.json()

    async def test_list_with_category_filter(self, client, db, make_contact):
        await make_contact(name="Inv Person", category="investor")
        await make_contact(name="Cli Person", category="client")

        resp = await client.get("/api/contacts?category=investor")
        assert resp.status_code == 200
        contacts = resp.json()["contacts"]
        assert all(c["category"] == "investor" for c in contacts)

    async def test_list_respects_limit(self, client, db, make_contact):
        for i in range(5):
            await make_contact(name=f"Limited {i}")

        resp = await client.get("/api/contacts?limit=2")
        assert resp.status_code == 200
        assert len(resp.json()["contacts"]) <= 2


@pytest.mark.asyncio
class TestGetContact:
    async def test_get_existing(self, client, db, make_contact):
        contact = await make_contact(name="Detail Person", company="DetailCo")
        resp = await client.get(f"/api/contacts/{contact.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["contact"]["name"] == "Detail Person"
        assert "interactions" in body

    async def test_get_nonexistent_returns_404(self, client):
        resp = await client.get(f"/api/contacts/{ABSENT_CONTACT_ID}")
        assert resp.status_code == 404

    async def test_get_malformed_id_returns_422(self, client):
        """A well-formed request for a missing row is 404; a malformed id is 422."""
        resp = await client.get(f"/api/contacts/{MALFORMED_CONTACT_ID}")
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestUpdateContact:
    async def test_update_fields(self, client, db, make_contact):
        contact = await make_contact(name="Update Me")
        resp = await client.patch(
            f"/api/contacts/{contact.id}",
            json={"company": "UpdatedCorp", "role": "CTO"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["contact"]["company"] == "UpdatedCorp"
        assert body["contact"]["role"] == "CTO"

    async def test_update_nonexistent_returns_404(self, client):
        resp = await client.patch(
            f"/api/contacts/{ABSENT_CONTACT_ID}",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404

    async def test_update_malformed_id_returns_422(self, client):
        resp = await client.patch(
            f"/api/contacts/{MALFORMED_CONTACT_ID}",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestDeleteContact:
    async def test_delete_existing(self, client, db, make_contact):
        contact = await make_contact(name="Delete Me")
        resp = await client.delete(f"/api/contacts/{contact.id}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_delete_nonexistent_returns_404(self, client):
        resp = await client.delete(f"/api/contacts/{ABSENT_CONTACT_ID}")
        assert resp.status_code == 404

    async def test_delete_malformed_id_returns_422(self, client):
        resp = await client.delete(f"/api/contacts/{MALFORMED_CONTACT_ID}")
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestContactReminders:
    async def test_set_reminder(self, client, db, make_contact):
        contact = await make_contact(name="Reminder Person")
        resp = await client.post(f"/api/contacts/{contact.id}/set-reminder?frequency=weekly")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["reminder_frequency"] == "weekly"
        assert body["next_reminder_at"] is not None

    async def test_clear_reminder(self, client, db, make_contact):
        contact = await make_contact(name="Clear Reminder")
        # Set first
        await client.post(f"/api/contacts/{contact.id}/set-reminder?frequency=weekly")
        # Then clear
        resp = await client.post(f"/api/contacts/{contact.id}/set-reminder?frequency=none")
        assert resp.status_code == 200
        assert resp.json()["reminder_frequency"] is None

    async def test_invalid_frequency_rejected(self, client, db, make_contact):
        contact = await make_contact(name="Bad Frequency")
        resp = await client.post(f"/api/contacts/{contact.id}/set-reminder?frequency=invalid")
        assert resp.status_code == 422

    async def test_mark_contacted(self, client, db, make_contact):
        contact = await make_contact(name="Contacted Person")
        resp = await client.post(f"/api/contacts/{contact.id}/mark-contacted")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_set_reminder_nonexistent_returns_404(self, client):
        resp = await client.post(f"/api/contacts/{ABSENT_CONTACT_ID}/set-reminder?frequency=weekly")
        assert resp.status_code == 404
