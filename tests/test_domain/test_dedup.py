"""
Test: Contact deduplication service behaviors.

Uses FAKE DB + real dedup logic (no mocks).
The dedup service is pure domain logic that queries the DB — no foreign systems.

Behaviors:
  - "dedup finds existing contact by email"
  - "dedup finds existing contact by name + company"
  - "dedup returns None when no match exists"
  - "merge_or_create updates existing contact with new fields"
  - "merge_or_create creates new contact when no duplicate"
"""

import pytest

from src.schemas.contacts import ExtractedContactData
from src.services.dedup import find_duplicate, merge_or_create
from tests.conftest import TENANT_ID


@pytest.mark.asyncio
class TestFindDuplicate:
    async def test_finds_by_email(self, db, make_contact):
        await make_contact(name="Dedup Email", email="dedup@test.com")

        extracted = ExtractedContactData(name="Dedup Email", email="dedup@test.com")
        dup = await find_duplicate(db, extracted, TENANT_ID)
        assert dup is not None
        assert dup.email == "dedup@test.com"

    async def test_finds_by_name_and_company(self, db, make_contact):
        await make_contact(name="Dedup Name", company="DedupCorp")

        extracted = ExtractedContactData(name="Dedup Name", company="DedupCorp")
        dup = await find_duplicate(db, extracted, TENANT_ID)
        assert dup is not None

    async def test_no_match(self, db, make_contact):
        await make_contact(name="Existing", email="existing@test.com")

        extracted = ExtractedContactData(name="Brand New Person", email="new@test.com")
        dup = await find_duplicate(db, extracted, TENANT_ID)
        assert dup is None

    async def test_name_only_match(self, db, make_contact):
        await make_contact(name="Solo Name")

        extracted = ExtractedContactData(name="Solo Name")
        dup = await find_duplicate(db, extracted, TENANT_ID)
        assert dup is not None


@pytest.mark.asyncio
class TestMergeOrCreate:
    async def test_merges_new_fields_into_existing(self, db, make_contact):
        existing = await make_contact(name="Merge Target", email="merge@test.com")

        extracted = ExtractedContactData(
            name="Merge Target",
            email="merge@test.com",
            company="NewCorp",
            role="VP",
        )
        contact, is_new = await merge_or_create(db, extracted, TENANT_ID)
        assert is_new is False
        assert contact.id == existing.id

    async def test_creates_when_no_duplicate(self, db):
        extracted = ExtractedContactData(
            name="Fresh Person",
            email="fresh@unique.com",
            company="UniqueInc",
        )
        contact, is_new = await merge_or_create(db, extracted, TENANT_ID)
        assert is_new is True
        assert contact.name == "Fresh Person"

    async def test_appends_context(self, db, make_contact):
        await make_contact(
            name="Context Person",
            email="ctx@test.com",
            context="Met at dinner",
        )

        extracted = ExtractedContactData(
            name="Context Person",
            email="ctx@test.com",
            context="Also met at conference",
        )
        contact, is_new = await merge_or_create(db, extracted, TENANT_ID)
        assert is_new is False

        # merge_or_create returns the original object reference which may be stale.
        # Re-query to verify the context was actually appended in the DB.
        from src.db.queries import contacts as contact_queries

        refreshed = await contact_queries.get_contact_by_id(db, contact.id, TENANT_ID)
        assert "dinner" in refreshed.context
        assert "conference" in refreshed.context
