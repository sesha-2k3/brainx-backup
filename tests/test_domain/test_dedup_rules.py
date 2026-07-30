"""
Test: duplicate-detection rules (behaviour change T2.4).

WHY THIS FILE EXISTS
--------------------
find_duplicate() previously contained this branch:

    # If only one has company, still consider it a match
    elif not company or not contact_company:
        logger.info(f"Found duplicate by name (partial company): {contact.id}")
        return contact

It was removed. Nothing in the suite covered it, so removing it broke no test —
which meant the old behaviour AND the new behaviour both passed, and the rule was
entirely unverified in either direction.

That is the worst possible coverage state for this particular function, because a
false positive here is the only defect in the codebase that DESTROYS DATA. A
missed merge leaves two records that can be joined deliberately later. A wrong
merge grafts one person's interaction history, tasks and reminders onto another
person's record, marks the proposal confirmed, and keeps no record of the split.

THE RULE, STATED ONCE
---------------------
Match on email -> duplicate. Match on phone -> duplicate. Otherwise, on an exact
name match:

    | extracted.company | existing.company | verdict                        |
    |-------------------|------------------|--------------------------------|
    | "Acme"            | "Acme"           | duplicate                      |
    | "Acme"            | "Globex"         | NOT a duplicate                |
    | None              | None             | duplicate (name is all we have)|
    | "Acme"            | None             | NOT a duplicate (ambiguous)    |
    | None              | "Acme"           | NOT a duplicate (ambiguous)    |

The last two rows are the behaviour change. They used to be duplicates.

PROVING RED
-----------
These tests are only meaningful if they fail against the old code. To see red,
restore the deleted branch in src/services/dedup.py, immediately after the
`elif not company and not contact_company:` block:

    elif not company or not contact_company:
        return contact

Then run:

    pytest tests/test_domain/test_dedup_rules.py -v

Expected red: test_extracted_has_company_existing_does_not_is_ambiguous,
test_existing_has_company_extracted_does_not_is_ambiguous, and
test_ambiguous_match_creates_a_second_contact all fail. Remove the branch again
and they pass. Everything else in the file stays green in both states — those are
the regression guards.

A NOTE ON ASSERTING `is None`
-----------------------------
A test that asserts "no duplicate was found" can pass for the wrong reason: if
search_contacts_by_name() returned no candidates, find_duplicate() never had
anything to reject and the assertion proves nothing about the rule. Every
ambiguity test below therefore first asserts the candidate IS retrievable by
name, so a passing test means the candidate was found and deliberately rejected.
"""

import pytest

from src.db.queries import contacts as contact_queries
from src.schemas.contacts import ExtractedContactData
from src.services.dedup import find_duplicate, merge_or_create


@pytest.mark.asyncio
class TestNameAndCompanyRules:
    """The five-row rule table above, one test per row."""

    async def test_same_name_same_company_is_a_duplicate(self, db, make_contact):
        existing = await make_contact(name="Dana Reed", company="Acme Corp")

        found = await find_duplicate(
            db, ExtractedContactData(name="Dana Reed", company="Acme Corp")
        )

        assert found is not None
        assert found.id == existing.id

    async def test_same_name_different_company_is_not_a_duplicate(self, db, make_contact):
        existing = await make_contact(name="Dana Reed", company="Acme Corp")

        # Prove the candidate is reachable, so `is None` below means "rejected",
        # not "never looked at".
        candidates = await contact_queries.search_contacts_by_name(db, "Dana Reed")
        assert any(c.id == existing.id for c in candidates)

        found = await find_duplicate(db, ExtractedContactData(name="Dana Reed", company="Globex"))

        assert found is None

    async def test_same_name_neither_has_company_is_a_duplicate(self, db, make_contact):
        existing = await make_contact(name="Solo Person")

        found = await find_duplicate(db, ExtractedContactData(name="Solo Person"))

        assert found is not None
        assert found.id == existing.id

    async def test_extracted_has_company_existing_does_not_is_ambiguous(self, db, make_contact):
        """
        BEHAVIOUR CHANGE. This returned the existing contact before.

        Realistic path: a contact was captured from a passing mention with no
        company, and now a business card arrives for a different person who
        happens to share the name.
        """
        existing = await make_contact(name="Chris Bell")

        candidates = await contact_queries.search_contacts_by_name(db, "Chris Bell")
        assert any(c.id == existing.id for c in candidates)

        found = await find_duplicate(db, ExtractedContactData(name="Chris Bell", company="Initech"))

        assert found is None

    async def test_existing_has_company_extracted_does_not_is_ambiguous(self, db, make_contact):
        """
        BEHAVIOUR CHANGE, mirror of the above. This is the direction that caused
        real damage: a voice note rarely states a company, so every casual
        mention of a common name used to merge into whichever record already
        existed.
        """
        existing = await make_contact(name="Chris Bell", company="Initech")

        candidates = await contact_queries.search_contacts_by_name(db, "Chris Bell")
        assert any(c.id == existing.id for c in candidates)

        found = await find_duplicate(db, ExtractedContactData(name="Chris Bell"))

        assert found is None


@pytest.mark.asyncio
class TestStrongSignalsOverrideCompanyAmbiguity:
    """
    Email and phone are checked before the name rules and are unaffected by the
    tightening. Tightening name matching must not have made dedup weaker where
    it has a genuinely reliable signal.
    """

    async def test_email_match_wins_even_when_companies_disagree(self, db, make_contact):
        existing = await make_contact(name="Pat Lane", email="pat@acme.com", company="Acme Corp")

        found = await find_duplicate(
            db,
            ExtractedContactData(
                name="Pat Lane", email="pat@acme.com", company="Totally Different Co"
            ),
        )

        assert found is not None
        assert found.id == existing.id

    async def test_email_match_wins_even_with_a_different_name(self, db, make_contact):
        """A married name or a nickname should not create a second record."""
        existing = await make_contact(name="Patricia Lane", email="pat@acme.com")

        found = await find_duplicate(
            db, ExtractedContactData(name="Pat Lane", email="pat@acme.com")
        )

        assert found is not None
        assert found.id == existing.id

    async def test_email_comparison_ignores_case_and_padding(self, db, make_contact):
        existing = await make_contact(name="Casey Fox", email="casey@acme.com")

        found = await find_duplicate(
            db, ExtractedContactData(name="Casey Fox", email="  CASEY@ACME.COM  ")
        )

        assert found is not None
        assert found.id == existing.id

    async def test_phone_match_wins_even_when_companies_disagree(self, db, make_contact):
        """
        Uses a genuinely valid US number, not a 555 one.

        555 exchanges fail phonenumbers validation, so normalize_phone() falls
        through to its digit-stripping fallback. A 555-based test would still
        pass, but it would be exercising the fallback rather than real E.164
        normalization — and would keep passing if actual normalization broke.

        The stored value must already be E.164 because create_contact() does not
        normalize on write, and find_duplicate_contact() compares the column
        against the normalized input with `==`.
        """
        existing = await make_contact(name="Rob Vale", phone="+12133734253", company="Acme Corp")

        found = await find_duplicate(
            db,
            ExtractedContactData(name="Rob Vale", phone="(213) 373-4253", company="Globex"),
        )

        assert found is not None, "the two formats must normalize to the same E.164 value"
        assert found.id == existing.id


@pytest.mark.asyncio
class TestNameComparisonNormalization:
    """
    The name and company compare is case- and whitespace-insensitive. Worth
    pinning: if normalization regressed, the ambiguity tests above would start
    passing for the wrong reason (no candidate found rather than rejected).
    """

    async def test_name_and_company_match_ignores_case(self, db, make_contact):
        existing = await make_contact(name="Dana Reed", company="Acme Corp")

        found = await find_duplicate(
            db, ExtractedContactData(name="DANA REED", company="ACME CORP")
        )

        assert found is not None
        assert found.id == existing.id

    async def test_name_and_company_match_ignores_surrounding_whitespace(self, db, make_contact):
        existing = await make_contact(name="Dana Reed", company="Acme Corp")

        found = await find_duplicate(
            db, ExtractedContactData(name="  Dana Reed  ", company="  Acme Corp  ")
        )

        assert found is not None
        assert found.id == existing.id

    async def test_partial_name_is_not_a_duplicate(self, db, make_contact):
        """
        search_contacts_by_name uses a substring ILIKE, so "Dana" retrieves
        "Dana Reed" as a CANDIDATE. find_duplicate must still require an exact
        name match before merging.
        """
        existing = await make_contact(name="Dana Reed")

        candidates = await contact_queries.search_contacts_by_name(db, "Dana")
        assert any(c.id == existing.id for c in candidates), "candidate must be retrievable"

        found = await find_duplicate(db, ExtractedContactData(name="Dana"))

        assert found is None


@pytest.mark.asyncio
class TestNoSignalAtAll:
    async def test_no_identifying_fields_returns_none(self, db, make_contact):
        await make_contact(name="Someone Real")

        found = await find_duplicate(db, ExtractedContactData())

        assert found is None

    async def test_unknown_person_returns_none(self, db, make_contact):
        await make_contact(name="Known Person", email="known@acme.com")

        found = await find_duplicate(
            db, ExtractedContactData(name="Complete Stranger", email="stranger@nowhere.com")
        )

        assert found is None


@pytest.mark.asyncio
class TestMergeOrCreateFollowsTheSameRules:
    """
    find_duplicate() returning None is only half the story — the consequence is
    what the user experiences. merge_or_create() must create a SECOND record
    rather than merging, and both records must survive independently.
    """

    async def test_ambiguous_match_creates_a_second_contact(self, db, make_contact):
        """
        BEHAVIOUR CHANGE, told as the scenario that motivated it.

        Monday:   a business card is scanned  -> David Kim, Sequoia Capital
        Thursday: a voice note is captured    -> "Met David Kim at the meetup,
                                                  wants a demo"  (no company)

        Under the old rule the Thursday capture merged into the investor's
        record, and the prospect's note, task and reminder were attached to the
        wrong person with no way back.
        """
        investor = await make_contact(
            name="David Kim", company="Sequoia Capital", category="investor"
        )

        prospect, is_new = await merge_or_create(
            db, ExtractedContactData(name="David Kim", context="Met at the meetup")
        )

        assert is_new is True, "the ambiguous capture must not merge into the investor"
        assert prospect.id != investor.id

        # Both records exist independently, and the investor is untouched.
        untouched = await contact_queries.get_contact_by_id(db, investor.id)
        assert untouched.company == "Sequoia Capital"
        assert untouched.category == "investor"
        assert untouched.context is None, "the prospect's context must not leak across"

    async def test_confident_match_still_merges_and_fills_blanks(self, db, make_contact):
        """The tightening must not have broken merging where it is warranted."""
        existing = await make_contact(name="Erin Shaw", company="Acme Corp")

        merged, is_new = await merge_or_create(
            db,
            ExtractedContactData(
                name="Erin Shaw",
                company="Acme Corp",
                email="erin@acme.com",
                role="CTO",
            ),
        )

        assert is_new is False
        assert merged.id == existing.id
        assert merged.email == "erin@acme.com"
        assert merged.role == "CTO"

    async def test_merge_does_not_overwrite_existing_values(self, db, make_contact):
        """Merging fills empty fields; it never replaces data already recorded."""
        existing = await make_contact(name="Erin Shaw", company="Acme Corp", role="VP Engineering")

        merged, is_new = await merge_or_create(
            db,
            ExtractedContactData(name="Erin Shaw", company="Acme Corp", role="Intern"),
        )

        assert is_new is False
        # Ruff F841 flagged `existing` as assigned-but-unused here, which was a
        # real gap rather than style noise: without this line the test proves
        # only that SOMETHING was merged, not that it merged into the contact
        # the test set up. A bug that merged into the wrong record would still
        # have satisfied `is_new is False`.
        assert merged.id == existing.id
        assert merged.role == "VP Engineering", "an existing value must not be replaced"
        assert merged.company == "Acme Corp"

    async def test_merge_appends_context_rather_than_replacing_it(self, db, make_contact):
        """
        Context accumulates across encounters. This is one of the behaviours the
        inline merge in confirm_proposal was missing before it was replaced by a
        call to merge_or_create.
        """
        await make_contact(name="Erin Shaw", company="Acme Corp", context="Met at TechCrunch")

        merged, _ = await merge_or_create(
            db,
            ExtractedContactData(
                name="Erin Shaw", company="Acme Corp", context="Reconnected at the summit"
            ),
        )

        assert "Met at TechCrunch" in merged.context
        assert "Reconnected at the summit" in merged.context

    async def test_repeated_identical_context_is_not_duplicated(self, db, make_contact):
        await make_contact(name="Erin Shaw", company="Acme Corp", context="Met at TechCrunch")

        merged, _ = await merge_or_create(
            db,
            ExtractedContactData(
                name="Erin Shaw", company="Acme Corp", context="Met at TechCrunch"
            ),
        )

        assert merged.context.count("Met at TechCrunch") == 1


@pytest.mark.asyncio
class TestKnownDefectInEmailPhoneLookup:
    """
    A pre-existing bug, unrelated to the T2.4 tightening, found while writing
    the tests above.

    contact_queries.find_duplicate_contact() builds:

        select(Contact).where(or_(Contact.email == email, Contact.phone == phone))

    and reads the result with .scalar_one_or_none() — with no .limit(1). If the
    email matches one contact and the phone matches a DIFFERENT one, the query
    returns two rows and SQLAlchemy raises MultipleResultsFound, which surfaces
    as an HTTP 500 from /api/proposals/{id}/confirm.

    It is reachable without anything exotic: two people sharing an office landline,
    a family sharing a home number, or an email typed onto the wrong record. The
    user experience is that confirming a capture fails outright, with a server
    error rather than a duplicate prompt.

    The fix is a decision about precedence, not just a .limit(1): email is the
    stronger signal, so it should probably be checked first and the phone lookup
    only consulted if email finds nothing. Marked xfail(strict=True) rather than
    left failing so the suite stays green — and so that fixing it turns this into
    an XPASS failure, prompting removal of the marker.
    """

    @pytest.mark.xfail(
        strict=True,
        reason="find_duplicate_contact uses scalar_one_or_none() over an OR of two "
        "conditions with no limit; two distinct matches raise MultipleResultsFound",
    )
    async def test_email_and_phone_matching_different_contacts(self, db, make_contact):
        await make_contact(name="Alex One", email="shared.office@acme.com")
        await make_contact(name="Blake Two", phone="+12133734253")

        # Email points at Alex, phone points at Blake. Exactly one contact should
        # be returned (email is the stronger signal), not an exception.
        found = await find_duplicate(
            db,
            ExtractedContactData(
                name="Casey Three",
                email="shared.office@acme.com",
                phone="(213) 373-4253",
            ),
        )

        assert found is not None
        assert found.email == "shared.office@acme.com"
