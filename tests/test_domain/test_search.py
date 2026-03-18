"""
Test: Cross-entity search behaviors.

Behaviors:
  - "search_all finds contacts and interactions matching query"
  - "category filtering returns correct contacts"
  - "company-based interaction lookup works via subquery"
  - "recent activity returns interactions from last N days"
  - "contact with interactions returns combined data"
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.db.queries import search as search_queries


@pytest.mark.asyncio
class TestSearchAll:
    async def test_finds_contacts_by_name(self, db, make_contact):
        await make_contact(name="Searchable Sam", company="SearchCo")

        results = await search_queries.search_all(db, "sam")
        assert len(results["contacts"]) >= 1

    async def test_finds_interactions_by_summary(self, db, make_contact, make_interaction):
        contact = await make_contact(name="Interactor")
        await make_interaction(contact.id, summary="Discussed quantum computing")

        results = await search_queries.search_all(db, "quantum")
        assert len(results["interactions"]) >= 1

    async def test_empty_query_returns_empty(self, db):
        results = await search_queries.search_all(db, "  ")
        assert results["contacts"] == []
        assert results["interactions"] == []


@pytest.mark.asyncio
class TestCategoryFilter:
    async def test_filter_by_category(self, db, make_contact):
        await make_contact(name="Inv1", category="investor")
        await make_contact(name="Cli1", category="client")

        investors = await search_queries.get_contacts_by_category(db, "investor")
        assert all(c.category == "investor" for c in investors)


@pytest.mark.asyncio
class TestCompanyInteractions:
    async def test_find_interactions_by_company(self, db, make_contact, make_interaction):
        contact = await make_contact(name="CompanyPerson", company="BigCorp")
        await make_interaction(contact.id, summary="Met at BigCorp office")

        results = await search_queries.get_interactions_by_company(db, "BigCorp")
        assert len(results) >= 1

    async def test_empty_company_returns_empty(self, db):
        results = await search_queries.get_interactions_by_company(db, "  ")
        assert results == []


@pytest.mark.asyncio
class TestRecentActivity:
    async def test_returns_recent_only(self, db, make_contact, make_interaction):
        contact = await make_contact(name="Recent Guy")
        now = datetime.now(UTC)

        await make_interaction(contact.id, summary="Today", occurred_at=now)
        await make_interaction(
            contact.id,
            summary="Long ago",
            occurred_at=now - timedelta(days=30),
        )

        results = await search_queries.get_recent_activity(db, days=7)
        summaries = [r.summary for r in results]
        assert "Today" in summaries
        assert "Long ago" not in summaries


@pytest.mark.asyncio
class TestContactWithInteractions:
    async def test_returns_contact_and_interactions(self, db, make_contact, make_interaction):
        contact = await make_contact(name="Full Profile")
        await make_interaction(contact.id, summary="Meeting 1")
        await make_interaction(contact.id, summary="Meeting 2")

        result = await search_queries.get_contact_with_interactions(db, contact.id)
        assert result is not None
        assert result["contact"].name == "Full Profile"
        assert len(result["interactions"]) == 2

    async def test_nonexistent_returns_none(self, db):
        result = await search_queries.get_contact_with_interactions(db, "nonexistent")
        assert result is None
