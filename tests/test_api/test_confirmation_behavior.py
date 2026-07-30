"""
Test: /api/proposals/{id}/confirm behaviour changes.

Covers three changes that all live in the same code path:

  T1.5  duplicate detection runs on the CONFIRMED data (what the user approved),
        not on proposal.extracted_data (what the LLM originally guessed)
  T2.1  the endpoint delegates to merge_or_create() instead of reimplementing
        merge semantics inline — so context-appending applies here too
  N3    empty strings from the review form are stored as NULL, not ""

WHY T1.5 IS THE ONE TO GET RIGHT
--------------------------------
The endpoint used to dedup against one source of truth and write from another:

    extracted = ExtractedContactData(**proposal.extracted_data)  # LLM's guess
    duplicate = await find_duplicate(db, extracted)              # matched on THIS
    contact = await contact_queries.create_contact(db, name=data.name, ...)  # wrote THIS

So the bug only fires when the user CORRECTS something on the review screen —
which is precisely the careful path nobody thinks to test. Both directions are
covered below, because they fail in opposite and equally bad ways:

  - a correction that SHOULD cause a merge was ignored  -> duplicate contact
  - a correction that SHOULD prevent a merge was ignored -> wrong record edited

PROVING RED
-----------
To see these fail against the old behaviour, change the payload construction in
src/services/confirmation.py back to reading from the proposal:

    extracted = ExtractedContactData(**{
        k: v for k, v in proposal.extracted_data.items() if k != "raw_text"
    })
    contact, was_created = await merge_or_create(db, extracted)

Expected red: test_correcting_an_email_lets_dedup_find_the_existing_contact and
test_correcting_an_email_prevents_merging_into_the_wrong_contact.

NOTE ON FIXTURE NAMES
---------------------
The name recorded on the existing contact in the first test differs slightly
from the extracted name ("Sarah J. Chen" vs "Sarah Chen") on purpose. That makes
the name+company rules unable to match in either direction, so the assertion is
isolated to the email — otherwise the old code would merge via the name path and
the test would pass for the wrong reason.
"""

import pytest

from src.db.queries import contacts as contact_queries
from src.db.queries import proposals as proposal_queries


@pytest.mark.asyncio
class TestDedupUsesConfirmedData:
    async def test_correcting_an_email_lets_dedup_find_the_existing_contact(
        self, client, db, make_contact
    ):
        """
        OCR misreads globex.io as globcx.io. The user spots it and fixes it on the
        review screen. That correction must feed duplicate detection, or the
        careful user is punished with a second copy of a contact they already have.
        """
        existing = await make_contact(name="Sarah J. Chen", email="sarah@globex.io")
        before = len(await contact_queries.list_contacts(db, limit=100))

        proposal = await proposal_queries.create_proposal(
            db,
            source_type="image",
            extracted_data={"name": "Sarah Chen", "email": "sarah@globcx.io"},
        )

        resp = await client.post(
            f"/api/proposals/{proposal.id}/confirm",
            json={"name": "Sarah Chen", "email": "sarah@globex.io", "tasks": []},
        )

        assert resp.status_code == 200
        # The corrected email must be what dedup matched on.
        assert resp.json()["contact_id"] == existing.id, "corrected email should match"

        after = len(await contact_queries.list_contacts(db, limit=100))
        assert after == before, "no second contact should have been created"

    async def test_correcting_an_email_prevents_merging_into_the_wrong_contact(
        self, client, db, make_contact
    ):
        """
        The opposite failure, and the more destructive one.

        The LLM produces an email that belongs to somebody else already in the
        database. The user replaces it with the right one. Deduping on the stale
        extracted value would merge this new person INTO that unrelated record —
        editing a contact the user never referred to.
        """
        unrelated = await make_contact(name="Marcus Webb", email="shared@oldco.com")

        proposal = await proposal_queries.create_proposal(
            db,
            source_type="text",
            extracted_data={"name": "Nina Patel", "email": "shared@oldco.com"},
        )

        resp = await client.post(
            f"/api/proposals/{proposal.id}/confirm",
            json={"name": "Nina Patel", "email": "nina@newco.com", "tasks": []},
        )

        assert resp.status_code == 200
        assert resp.json()["contact_id"] != unrelated.id
        assert resp.json()["contact_name"] == "Nina Patel"

        # The unrelated contact must be exactly as it was.
        untouched = await contact_queries.get_contact_by_id(db, unrelated.id)
        assert untouched.name == "Marcus Webb"
        assert untouched.email == "shared@oldco.com"

    async def test_confirming_unchanged_data_still_merges(self, client, db, make_contact):
        """Regression guard: the common path, where the user changes nothing."""
        existing = await make_contact(name="Owen Lark", email="owen@acme.com")

        proposal = await proposal_queries.create_proposal(
            db,
            source_type="text",
            extracted_data={"name": "Owen Lark", "email": "owen@acme.com"},
        )

        resp = await client.post(
            f"/api/proposals/{proposal.id}/confirm",
            json={"name": "Owen Lark", "email": "owen@acme.com", "tasks": []},
        )

        assert resp.status_code == 200
        assert resp.json()["contact_id"] == existing.id


@pytest.mark.asyncio
class TestEmptyStringsBecomeNull:
    """
    N3. ExtractionPreview initializes every field to "" and submits the whole
    form, so untouched fields arrive as empty strings rather than as missing keys.

    Stored as "", they poison duplicate detection permanently: find_duplicate
    compares with `Contact.email == email`, and "" never equals a real address.
    Email is the strongest dedup signal, so it would be silently disabled for
    every contact captured without one.
    """

    async def test_blank_optional_fields_are_stored_as_null(self, client, db):
        proposal = await proposal_queries.create_proposal(
            db,
            source_type="text",
            extracted_data={"name": "Blank Fields"},
        )

        resp = await client.post(
            f"/api/proposals/{proposal.id}/confirm",
            json={
                "name": "Blank Fields",
                "email": "",
                "phone": "",
                "company": "",
                "role": "",
                "website": "",
                "context": "",
                "tasks": [],
            },
        )

        assert resp.status_code == 200
        contact = await contact_queries.get_contact_by_id(db, resp.json()["contact_id"])

        assert contact.email is None
        assert contact.phone is None
        assert contact.company is None
        assert contact.role is None
        assert contact.website is None
        assert contact.context is None

    async def test_whitespace_only_fields_are_stored_as_null(self, client, db):
        proposal = await proposal_queries.create_proposal(
            db, source_type="text", extracted_data={"name": "Padded"}
        )

        resp = await client.post(
            f"/api/proposals/{proposal.id}/confirm",
            json={"name": "Padded", "email": "   ", "company": "  ", "tasks": []},
        )

        assert resp.status_code == 200
        contact = await contact_queries.get_contact_by_id(db, resp.json()["contact_id"])
        assert contact.email is None
        assert contact.company is None

    async def test_a_blank_email_does_not_break_later_dedup(self, client, db):
        """
        The consequence, made explicit. A contact captured with no email must
        still be matchable by email once one is learned — impossible if "" was
        stored, because "" never equals a real address.
        """
        first = await proposal_queries.create_proposal(
            db, source_type="text", extracted_data={"name": "Ada Byron"}
        )
        resp = await client.post(
            f"/api/proposals/{first.id}/confirm",
            json={"name": "Ada Byron", "email": "", "tasks": []},
        )
        contact_id = resp.json()["contact_id"]

        # Later, a business card supplies the email.
        second = await proposal_queries.create_proposal(
            db, source_type="image", extracted_data={"name": "Ada Byron"}
        )
        resp2 = await client.post(
            f"/api/proposals/{second.id}/confirm",
            json={"name": "Ada Byron", "email": "ada@analytical.org", "tasks": []},
        )

        assert resp2.status_code == 200
        # Merges on the name (neither side has a company), then fills the email.
        assert resp2.json()["contact_id"] == contact_id, "should merge, then fill email"

        merged = await contact_queries.get_contact_by_id(db, contact_id)
        assert merged.email == "ada@analytical.org"


@pytest.mark.asyncio
class TestMergeSemanticsApplyOnConfirm:
    """
    T2.1. The endpoint reimplemented merging inline, without context-appending or
    phone/email normalization, so merging via the confirm screen behaved
    differently from merging anywhere else. It now calls merge_or_create().
    """

    async def test_context_is_appended_not_replaced(self, client, db, make_contact):
        existing = await make_contact(
            name="Iris Vale", email="iris@acme.com", context="Met at TechCrunch"
        )

        proposal = await proposal_queries.create_proposal(
            db, source_type="text", extracted_data={"name": "Iris Vale"}
        )

        resp = await client.post(
            f"/api/proposals/{proposal.id}/confirm",
            json={
                "name": "Iris Vale",
                "email": "iris@acme.com",
                "context": "Reconnected at the summit",
                "tasks": [],
            },
        )

        assert resp.status_code == 200
        merged = await contact_queries.get_contact_by_id(db, existing.id)
        assert "Met at TechCrunch" in merged.context
        assert "Reconnected at the summit" in merged.context

    async def test_existing_values_are_not_overwritten_on_confirm(self, client, db, make_contact):
        existing = await make_contact(
            name="Iris Vale", email="iris@acme.com", role="VP Engineering"
        )

        proposal = await proposal_queries.create_proposal(
            db, source_type="text", extracted_data={"name": "Iris Vale"}
        )

        resp = await client.post(
            f"/api/proposals/{proposal.id}/confirm",
            json={
                "name": "Iris Vale",
                "email": "iris@acme.com",
                "role": "Intern",
                "tasks": [],
            },
        )

        assert resp.status_code == 200
        merged = await contact_queries.get_contact_by_id(db, existing.id)
        assert merged.role == "VP Engineering"


@pytest.mark.asyncio
class TestInferredInputIsClampedNotRejected:
    """
    The other half of the validation split (see R3.1 in test_validation_contract).

    POST/PATCH /api/contacts REJECT an unknown category with a 422, because a
    human or an API client typed it and silently discarding it means they never
    learn it had no effect.

    This path is different: the value originated from LLM extraction, so it is
    clamped to null instead. A model's bad guess must not reject the whole
    capture — the user would lose a transcript they cannot reproduce.
    """

    async def test_unknown_category_is_clamped_to_null_not_rejected(self, client, db):
        proposal = await proposal_queries.create_proposal(
            db, source_type="text", extracted_data={"name": "Vendor Person"}
        )

        resp = await client.post(
            f"/api/proposals/{proposal.id}/confirm",
            json={"name": "Vendor Person", "category": "vendor", "tasks": []},
        )

        assert resp.status_code == 200, "an invalid inferred category must not 422"
        contact = await contact_queries.get_contact_by_id(db, resp.json()["contact_id"])
        assert contact.category is None

    async def test_valid_category_survives_confirm(self, client, db):
        proposal = await proposal_queries.create_proposal(
            db, source_type="text", extracted_data={"name": "Client Person"}
        )

        resp = await client.post(
            f"/api/proposals/{proposal.id}/confirm",
            json={"name": "Client Person", "category": "client", "tasks": []},
        )

        assert resp.status_code == 200
        contact = await contact_queries.get_contact_by_id(db, resp.json()["contact_id"])
        assert contact.category == "client"
