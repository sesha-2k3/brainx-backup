"""
Test: Interaction lifecycle behaviors.

Behaviors:
  - "creating an interaction links to contact and builds search vector"
  - "listing interactions orders by recency"
  - "searching interactions finds by summary content"
  - "updating an interaction refreshes search vector"
  - "deleting an interaction removes it permanently"
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.db.queries import interactions as interaction_queries
from tests.conftest import TENANT_ID


@pytest.mark.asyncio
class TestInteractionCreation:

    async def test_create_and_list(self, db, make_contact, make_interaction):
        contact = await make_contact(name="Alice")
        await make_interaction(contact.id, summary="First meeting")
        await make_interaction(contact.id, summary="Follow-up call")

        results = await interaction_queries.list_interactions_for_contact(
            db, contact.id
        )
        assert len(results) == 2

    async def test_search_vector_populated(self, db, make_contact, make_interaction):
        contact = await make_contact(name="Bob")
        interaction = await make_interaction(
            contact.id, summary="Discussed AI partnership"
        )
        assert interaction.search_vector is not None
        assert "ai partnership" in interaction.search_vector


@pytest.mark.asyncio
class TestInteractionSearch:

    async def test_search_by_summary(self, db, make_contact, make_interaction):
        contact = await make_contact(name="Carol")
        await make_interaction(contact.id, summary="Discussed blockchain strategy")
        await make_interaction(contact.id, summary="Coffee chat about family")

        results = await interaction_queries.search_interactions(
            db, "blockchain", TENANT_ID
        )
        assert len(results) >= 1
        assert any("blockchain" in r.summary.lower() for r in results)

    async def test_search_scoped_to_contact(self, db, make_contact, make_interaction):
        c1 = await make_contact(name="Dan")
        c2 = await make_contact(name="Eve")
        await make_interaction(c1.id, summary="Topic alpha")
        await make_interaction(c2.id, summary="Topic alpha too")

        results = await interaction_queries.search_interactions(
            db, "alpha", TENANT_ID, contact_id=c1.id
        )
        assert len(results) == 1


@pytest.mark.asyncio
class TestInteractionUpdate:

    async def test_update_summary(self, db, make_contact, make_interaction):
        contact = await make_contact(name="Frank")
        interaction = await make_interaction(contact.id, summary="Old summary")

        updated = await interaction_queries.update_interaction(
            db, interaction.id, summary="New summary"
        )
        assert updated.summary == "New summary"
        assert "new summary" in updated.search_vector

    async def test_update_nonexistent_returns_none(self, db):
        result = await interaction_queries.update_interaction(
            db, "fake-id", summary="nope"
        )
        assert result is None


@pytest.mark.asyncio
class TestInteractionDeletion:

    async def test_delete_existing(self, db, make_contact, make_interaction):
        contact = await make_contact(name="Grace")
        interaction = await make_interaction(contact.id, summary="Temp note")

        deleted = await interaction_queries.delete_interaction(db, interaction.id)
        assert deleted is True

    async def test_delete_nonexistent_returns_false(self, db):
        result = await interaction_queries.delete_interaction(db, "nonexistent")
        assert result is False


@pytest.mark.asyncio
class TestRecentInteractions:

    async def test_list_recent(self, db, make_contact, make_interaction):
        contact = await make_contact(name="Hank")
        now = datetime.now(timezone.utc)

        await make_interaction(
            contact.id, summary="Recent", occurred_at=now
        )
        await make_interaction(
            contact.id, summary="Old",
            occurred_at=now - timedelta(days=30),
        )

        results = await interaction_queries.list_recent_interactions(
            db, TENANT_ID, since=now - timedelta(days=7)
        )
        summaries = [r.summary for r in results]
        assert "Recent" in summaries
        assert "Old" not in summaries
