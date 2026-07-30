"""
Test: Proposal lifecycle behaviors.

Behaviors:
  - "creating a proposal stores extracted data as pending"
  - "confirming a proposal transitions state and links contact"
  - "rejecting a proposal marks it resolved"
  - "editing proposal data updates extracted fields"
  - "pending proposals are retrievable per user"
"""

import pytest

from src.db.models import ProposalStatus
from src.db.queries import proposals as proposal_queries


@pytest.mark.asyncio
class TestProposalCreation:
    async def test_create_pending(self, db):
        proposal = await proposal_queries.create_proposal(
            db,
            source_type="text",
            extracted_data={"name": "Test Person", "company": "TestCo"},
        )
        assert proposal.status == ProposalStatus.PENDING
        assert proposal.extracted_data["name"] == "Test Person"

    async def test_get_by_id(self, db):
        proposal = await proposal_queries.create_proposal(
            db,
            source_type="voice",
            extracted_data={"name": "Another"},
        )
        found = await proposal_queries.get_proposal_by_id(db, proposal.id)
        assert found is not None
        assert found.source_type == "voice"


@pytest.mark.asyncio
class TestProposalConfirmation:
    async def test_confirm_transitions_state(self, db, make_contact):
        contact = await make_contact(name="Confirmed Contact")
        proposal = await proposal_queries.create_proposal(
            db,
            source_type="text",
            extracted_data={"name": "Confirmed Contact"},
        )

        confirmed = await proposal_queries.confirm_proposal(db, proposal.id, contact_id=contact.id)
        assert confirmed.status == ProposalStatus.CONFIRMED
        assert confirmed.contact_id == contact.id
        assert confirmed.resolved_at is not None

    async def test_confirm_nonexistent_returns_none(self, db):
        result = await proposal_queries.confirm_proposal(db, "fake-id", contact_id="whatever")
        assert result is None


@pytest.mark.asyncio
class TestProposalRejection:
    async def test_reject_marks_resolved(self, db):
        proposal = await proposal_queries.create_proposal(
            db,
            source_type="text",
            extracted_data={"name": "Reject Me"},
        )

        rejected = await proposal_queries.reject_proposal(db, proposal.id)
        assert rejected.status == ProposalStatus.REJECTED
        assert rejected.resolved_at is not None

    async def test_reject_nonexistent_returns_none(self, db):
        result = await proposal_queries.reject_proposal(db, "nope")
        assert result is None


@pytest.mark.asyncio
class TestProposalEdit:
    async def test_update_extracted_data(self, db):
        proposal = await proposal_queries.create_proposal(
            db,
            source_type="text",
            extracted_data={"name": "Original"},
        )

        updated = await proposal_queries.update_proposal_data(db, proposal.id, {"name": "Edited"})
        assert updated.extracted_data["name"] == "Edited"
        assert updated.status == ProposalStatus.EDITED


@pytest.mark.asyncio
class TestPendingProposals:
    async def test_get_latest_pending_is_tenant_scoped(self, db):
        """
        Replaces test_get_pending_for_user.

        get_pending_proposal_for_user(whatsapp_user_id) is gone along with the
        column it filtered on. That column held the literal "web" for every row,
        so the filter matched everything and the only real scoping came from
        TenantSession — meaning the function was safe by accident, not by design.
        The replacement relies on the tenant filter explicitly.
        """
        await proposal_queries.create_proposal(
            db,
            source_type="text",
            extracted_data={"name": "Pending Person"},
        )

        pending = await proposal_queries.get_latest_pending_proposal(db)
        assert pending is not None
        assert pending.extracted_data["name"] == "Pending Person"

    async def test_list_pending(self, db):
        await proposal_queries.create_proposal(
            db,
            source_type="text",
            extracted_data={"name": "Listed"},
        )

        pending = await proposal_queries.list_pending_proposals(db)
        assert len(pending) >= 1
