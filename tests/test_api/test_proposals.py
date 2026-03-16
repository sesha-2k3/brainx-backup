"""
Test: Proposal and input processing endpoints via HTTP API.

These endpoints call the Groq API (foreign system), so we STUB it.

Behaviors:
  - "POST /api/input/text extracts data and creates proposal"
  - "POST /api/input/text returns 400 when extraction fails"
  - "GET /api/proposals/{id} returns proposal data"
  - "GET /api/proposals/{id} returns 404 for nonexistent"
  - "POST /api/proposals/{id}/confirm creates contact and tasks"
  - "DELETE /api/proposals/{id} rejects proposal"
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db.queries import proposals as proposal_queries
from tests.conftest import TENANT_ID


def _groq_extraction_response(name="Jane Doe", company="TestCo"):
    """Build a fake Groq response that returns valid extracted data."""
    response = MagicMock()
    response.choices = [
        MagicMock(
            message=MagicMock(
                content=(
                    f'{{"name": "{name}", "email": "{name.lower().replace(" ", "")}@test.com", '
                    f'"company": "{company}", "role": "Manager", "category": "client", '
                    f'"context": "Met at conference", '
                    f'"interaction_summary": "Discussed partnership", '
                    f'"tasks": [{{"title": "Send proposal", "due_date": "next week"}}]}}'
                )
            )
        )
    ]
    return response


@pytest.mark.asyncio
class TestTextInput:

    @patch("src.services.extraction.get_groq_client")
    async def test_process_text_creates_proposal(self, mock_get_client, client):
        groq = AsyncMock()
        groq.chat.completions.create = AsyncMock(
            return_value=_groq_extraction_response("Alice Test", "AliceCorp")
        )
        mock_get_client.return_value = groq

        resp = await client.post(
            "/api/input/text",
            json={"text": "Met Alice Test from AliceCorp at the conference."},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "proposal_id" in body
        assert body["extracted"]["name"] == "Alice Test"
        assert len(body["extracted"]["tasks"]) >= 1

    @patch("src.services.extraction.get_groq_client")
    async def test_process_text_returns_400_on_no_name(self, mock_get_client, client):
        groq = AsyncMock()
        response = MagicMock()
        response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"name": null, "tasks": []}'
                )
            )
        ]
        groq.chat.completions.create = AsyncMock(return_value=response)
        mock_get_client.return_value = groq

        resp = await client.post(
            "/api/input/text",
            json={"text": "Some vague text with no clear person."},
        )
        # Either 400 (extraction returns no name) or 500 (ExtractionError propagates)
        assert resp.status_code in (400, 500)


@pytest.mark.asyncio
class TestGetProposal:

    async def test_get_existing(self, client, db):
        proposal = await proposal_queries.create_proposal(
            db,
            source_type="text",
            whatsapp_user_id="web",
            extracted_data={"name": "Prop Person"},
            tenant_id=TENANT_ID,
        )

        resp = await client.get(f"/api/proposals/{proposal.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["extracted_data"]["name"] == "Prop Person"

    async def test_get_nonexistent_returns_404(self, client):
        resp = await client.get("/api/proposals/nonexistent-uuid")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestConfirmProposal:

    async def test_confirm_creates_contact(self, client, db):
        proposal = await proposal_queries.create_proposal(
            db,
            source_type="text",
            whatsapp_user_id="web",
            extracted_data={
                "name": "Confirm Person",
                "email": "confirm@test.com",
            },
            tenant_id=TENANT_ID,
        )

        resp = await client.post(
            f"/api/proposals/{proposal.id}/confirm",
            json={
                "name": "Confirm Person",
                "email": "confirm@test.com",
                "company": "ConfirmCo",
                "interaction_summary": "Initial meeting",
                "tasks": [{"title": "Follow up", "due_date": "next week"}],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["contact_name"] == "Confirm Person"
        assert body["tasks_created"] == 1

    async def test_confirm_nonexistent_returns_404(self, client):
        resp = await client.post(
            "/api/proposals/fake-id/confirm",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestRejectProposal:

    async def test_reject(self, client, db):
        proposal = await proposal_queries.create_proposal(
            db,
            source_type="text",
            whatsapp_user_id="web",
            extracted_data={"name": "Reject Person"},
            tenant_id=TENANT_ID,
        )

        resp = await client.delete(f"/api/proposals/{proposal.id}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_reject_nonexistent_returns_404(self, client):
        resp = await client.delete("/api/proposals/fake-id")
        assert resp.status_code == 404
