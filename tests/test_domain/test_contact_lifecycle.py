"""
Test: Contact lifecycle behaviors.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.db.queries import contacts as contact_queries
from src.db.queries import search as search_queries


@pytest.mark.asyncio
class TestContactCreation:
    async def test_create_and_retrieve(self, db, make_contact):
        contact = await make_contact(name="Alice Smith", email="alice@example.com")

        found = await contact_queries.get_contact_by_id(db, contact.id)
        assert found is not None
        assert found.name == "Alice Smith"
        assert found.email == "alice@example.com"

    async def test_contact_is_findable_across_its_fields(self, db, make_contact):
        """
        Replaces test_search_vector_populated.

        That test asserted `contact.search_vector is not None` — but no such
        column exists on Contact, in models.py or in any migration. The write
        path assigned to the name anyway, and SQLAlchemy permits assignment to
        unmapped attributes, so it silently created a throwaway Python attribute
        that was never persisted. The test passed by reading back the value it
        had just watched being set in memory.

        In other words: the suite was GREEN against a bug, and would have stayed
        green no matter what the search behaviour did.

        This version asserts the behaviour that was actually wanted — the contact
        can be found by terms drawn from different fields — through the public
        search interface, so it cannot pass unless search really works.
        """
        contact = await make_contact(name="Bob Jones", company="Acme", notes="VIP customer")

        by_name = await search_queries.search_all(db, "bob jones")
        assert any(c.id == contact.id for c in by_name["contacts"])

        by_company = await search_queries.search_all(db, "acme")
        assert any(c.id == contact.id for c in by_company["contacts"])

        by_notes = await search_queries.search_all(db, "vip customer")
        assert any(c.id == contact.id for c in by_notes["contacts"])

    async def test_terms_may_span_separate_fields(self, db, make_contact):
        """
        The old concatenated search_vector required query terms to be contiguous
        in field order, so a search combining a name and a company silently
        matched nothing. match_all_terms requires each term to appear in some
        column, not all of them in one.
        """
        contact = await make_contact(name="Bob Jones", company="Acme")

        results = await search_queries.search_all(db, "jones acme")
        assert any(c.id == contact.id for c in results["contacts"])


@pytest.mark.asyncio
class TestDuplicateDetection:
    async def test_finds_by_email(self, db, make_contact):
        await make_contact(name="Charlie", email="charlie@test.com")
        dup = await contact_queries.find_duplicate_contact(db, email="charlie@test.com", phone=None)
        assert dup is not None
        assert dup.name == "Charlie"

    async def test_finds_by_phone(self, db, make_contact):
        await make_contact(name="Dana", phone="+15551234567")
        dup = await contact_queries.find_duplicate_contact(db, email=None, phone="+15551234567")
        assert dup is not None
        assert dup.name == "Dana"

    async def test_no_match_returns_none(self, db, make_contact):
        await make_contact(name="Eve", email="eve@test.com")
        dup = await contact_queries.find_duplicate_contact(db, email="nobody@test.com", phone=None)
        assert dup is None

    async def test_none_inputs_returns_none(self, db):
        result = await contact_queries.find_duplicate_contact(db, email=None, phone=None)
        assert result is None


@pytest.mark.asyncio
class TestContactSearch:
    async def test_search_by_name_case_insensitive(self, db, make_contact):
        await make_contact(name="Franklin Gomez")
        results = await contact_queries.search_contacts_by_name(db, "franklin")
        assert len(results) >= 1
        assert any(c.name == "Franklin Gomez" for c in results)

    async def test_search_partial_name(self, db, make_contact):
        await make_contact(name="Greta Van Fleet")
        results = await contact_queries.search_contacts_by_name(db, "Van")
        assert len(results) >= 1

    async def test_search_no_results(self, db, make_contact):
        results = await contact_queries.search_contacts_by_name(db, "ZZZNONEXISTENT")
        assert results == []


@pytest.mark.asyncio
class TestContactUpdate:
    async def test_update_fields(self, db, make_contact):
        contact = await make_contact(name="Harry", company="OldCorp")
        updated = await contact_queries.update_contact(
            db, contact.id, company="NewCorp", role="CEO"
        )
        assert updated.company == "NewCorp"
        assert updated.role == "CEO"

    async def test_update_makes_new_values_searchable(self, db, make_contact):
        """
        Replaces test_update_refreshes_search_vector. Same reasoning as above:
        the original read back an unmapped in-memory attribute. Searching real
        columns needs no refresh step at all, which is precisely why the
        denormalized column was removed rather than added.
        """
        contact = await make_contact(name="Ivy")
        await contact_queries.update_contact(db, contact.id, company="SecretCo")

        results = await search_queries.search_all(db, "secretco")
        assert any(c.id == contact.id for c in results["contacts"])

    async def test_update_nonexistent_returns_none(self, db):
        result = await contact_queries.update_contact(db, "nonexistent-id", name="Ghost")
        assert result is None


@pytest.mark.asyncio
class TestContactListing:
    async def test_list_respects_category_filter(self, db, make_contact):
        await make_contact(name="Investor Joe", category="investor")
        await make_contact(name="Client Jane", category="client")

        investors = await contact_queries.list_contacts(db, category="investor")
        assert all(c.category == "investor" for c in investors)

    async def test_list_respects_limit(self, db, make_contact):
        for i in range(5):
            await make_contact(name=f"Contact {i}")

        results = await contact_queries.list_contacts(db, limit=3)
        assert len(results) <= 3


class TestReminderCalculation:
    """Pure logic — no DB, no async."""

    def test_weekly(self):
        from_date = datetime(2025, 1, 1, tzinfo=UTC)
        result = contact_queries.calculate_next_reminder("weekly", from_date)
        assert result == from_date + timedelta(weeks=1)

    def test_every_3_days(self):
        from_date = datetime(2025, 1, 1, tzinfo=UTC)
        result = contact_queries.calculate_next_reminder("every_3_days", from_date)
        assert result == from_date + timedelta(days=3)

    def test_every_2_weeks(self):
        from_date = datetime(2025, 1, 1, tzinfo=UTC)
        result = contact_queries.calculate_next_reminder("every_2_weeks", from_date)
        assert result == from_date + timedelta(weeks=2)

    def test_monthly(self):
        from_date = datetime(2025, 1, 1, tzinfo=UTC)
        result = contact_queries.calculate_next_reminder("monthly", from_date)
        assert result == from_date + timedelta(days=30)

    def test_unknown_frequency_returns_none(self):
        result = contact_queries.calculate_next_reminder("biweekly_chaos")
        assert result is None
