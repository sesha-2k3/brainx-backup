"""
Test: Contact lifecycle behaviors.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.db.queries import contacts as contact_queries


@pytest.mark.asyncio
class TestContactCreation:
    async def test_create_and_retrieve(self, db, make_contact):
        contact = await make_contact(name="Alice Smith", email="alice@example.com")

        found = await contact_queries.get_contact_by_id(db, contact.id)
        assert found is not None
        assert found.name == "Alice Smith"
        assert found.email == "alice@example.com"

    async def test_search_vector_populated(self, db, make_contact):
        contact = await make_contact(name="Bob Jones", company="Acme", notes="VIP customer")
        assert contact.search_vector is not None
        assert "bob jones" in contact.search_vector
        assert "acme" in contact.search_vector
        assert "vip customer" in contact.search_vector


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

    async def test_update_refreshes_search_vector(self, db, make_contact):
        contact = await make_contact(name="Ivy")
        await contact_queries.update_contact(db, contact.id, company="SecretCo")
        refreshed = await contact_queries.get_contact_by_id(db, contact.id)
        assert "secretco" in refreshed.search_vector

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
