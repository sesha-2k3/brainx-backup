"""
Test: LLM extraction service — foreign system boundary.

This is where we STUB the Groq API. Per TDD principles, mocks/stubs are
reserved for foreign system integration. The Groq API is the foreign system.

Behaviors:
  - "extraction parses valid LLM JSON into ExtractedContactData"
  - "extraction handles markdown-wrapped JSON from LLM"
  - "extraction raises on missing name"
  - "safe extraction returns empty data on failure"
  - "text truncation is applied to oversized input"
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.contacts import ExtractedContactData
from src.services.extraction import (
    ExtractionError,
    extract_contact_data,
    extract_contact_data_safe,
)


def _make_groq_response(json_str: str):
    """Helper to build a canned Groq chat completion response."""
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=json_str))]
    return response


@pytest.mark.asyncio
class TestExtractContactData:
    @patch("src.services.extraction.get_groq_client")
    async def test_parses_valid_json(self, mock_get_client):
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            return_value=_make_groq_response(
                '{"name": "Alice", "email": "alice@example.com", '
                '"company": "AliceCorp", "role": "CEO", "category": "client", '
                '"context": "Networking event", '
                '"interaction_summary": "Discussed deal", '
                '"tasks": [{"title": "Follow up", "due_date": "tomorrow"}]}'
            )
        )
        mock_get_client.return_value = client

        result = await extract_contact_data("Met Alice at conference")
        assert isinstance(result, ExtractedContactData)
        assert result.name == "Alice"
        assert len(result.tasks) == 1
        assert result.tasks[0].title == "Follow up"

        # NOT result.email == "alice@example.com".
        #
        # EXTRACTION_PROMPT does not ask the LLM for email, phone or website -
        # those come from regex over the full untruncated text. The stub above
        # volunteers an email anyway, and extract_contact_data deliberately
        # normalizes unrequested output to None so the invariant "these fields
        # are regex-derived or empty" always holds.
        #
        # The input text here contains no email, so None is the correct result.
        # This assertion previously expected the LLM's value to survive, which
        # was the contract BEFORE the deterministic-pass refactor.
        assert result.email is None

    @patch("src.services.extraction.get_groq_client")
    async def test_handles_markdown_wrapped_json(self, mock_get_client):
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            return_value=_make_groq_response(
                '```json\n{"name": "Bob", "company": "BobInc", "tasks": []}\n```'
            )
        )
        mock_get_client.return_value = client

        result = await extract_contact_data("Met Bob")
        assert result.name == "Bob"

    @patch("src.services.extraction.get_groq_client")
    async def test_raises_on_missing_name(self, mock_get_client):
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            return_value=_make_groq_response(
                '{"name": null, "email": "noname@test.com", "tasks": []}'
            )
        )
        mock_get_client.return_value = client

        with pytest.raises(ExtractionError, match="No name"):
            await extract_contact_data("Some text without a clear name")

    @patch("src.services.extraction.get_groq_client")
    async def test_raises_on_invalid_json(self, mock_get_client):
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            return_value=_make_groq_response("this is not json at all")
        )
        mock_get_client.return_value = client

        with pytest.raises(ExtractionError, match="Invalid JSON"):
            await extract_contact_data("Some text")


@pytest.mark.asyncio
class TestExtractContactDataSafe:
    @patch("src.services.extraction.get_groq_client")
    async def test_returns_empty_on_failure(self, mock_get_client):
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(return_value=_make_groq_response("garbage"))
        mock_get_client.return_value = client

        result = await extract_contact_data_safe("Some text")
        assert isinstance(result, ExtractedContactData)
        assert result.name is None  # Graceful degradation


@pytest.mark.asyncio
class TestSemanticSearch:
    """
    Test: Semantic search service — foreign system boundary (Groq LLM).
    Stubs the Groq client to return predictable match indices.
    """

    @patch("src.services.semantic_search.get_groq_client")
    async def test_returns_matching_contacts(self, mock_get_client):
        from src.services.semantic_search import semantic_search_with_explanation

        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            return_value=_make_groq_response('{"matches": [1], "explanation": "Name match"}')
        )
        mock_get_client.return_value = client

        contacts = [
            {"name": "Alice", "company": "AliceCorp"},
            {"name": "Bob", "company": "BobInc"},
        ]
        result = await semantic_search_with_explanation("Alice", contacts)
        assert len(result["matches"]) == 1
        assert result["matches"][0]["name"] == "Alice"

    @patch("src.services.semantic_search.get_groq_client")
    async def test_empty_contacts_returns_empty(self, mock_get_client):
        from src.services.semantic_search import semantic_search_with_explanation

        result = await semantic_search_with_explanation("anything", [])
        assert result["matches"] == []

    @patch("src.services.semantic_search.get_groq_client")
    async def test_empty_query_returns_empty(self, mock_get_client):
        from src.services.semantic_search import semantic_search_with_explanation

        result = await semantic_search_with_explanation("", [{"name": "X"}])
        assert result["matches"] == []

    @patch("src.services.semantic_search.get_groq_client")
    async def test_handles_invalid_llm_json(self, mock_get_client):
        from src.services.semantic_search import semantic_search_with_explanation

        client = AsyncMock()
        client.chat.completions.create = AsyncMock(return_value=_make_groq_response("not json"))
        mock_get_client.return_value = client

        result = await semantic_search_with_explanation("test", [{"name": "X"}])
        assert result["matches"] == []


# ---------------------------------------------------------------------------
# Deterministic pass: regex fills fields the LLM is not asked for.
#
# These two tests moved here from tests/test_services/test_ocr.py, where they
# patched src.services.ocr.extract_contact_data wholesale and then asserted that
# process_business_card_bytes performed a regex merge. With extraction stubbed
# out, that merge cannot happen — and ocr.py no longer owns it in any case. The
# helper it relied on (_quick_extract) was deleted when extract_contact_data took
# over running the regex passes internally.
#
# Tested here they exercise the real merge with only the Groq boundary stubbed,
# which is where the behaviour actually lives.
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestDeterministicPassFillsContactDetails:
    @patch("src.services.extraction.get_groq_client")
    async def test_regex_supplies_email_llm_was_not_asked_for(self, mock_get_client):
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            return_value=_make_groq_response(
                '{"name": "Bob Smith", "company": "SomeCo", "role": null, '
                '"category": null, "context": null, '
                '"interaction_summary": null, "tasks": []}'
            )
        )
        mock_get_client.return_value = client

        result = await extract_contact_data("Bob Smith\nbob@company.com\nSomeCo")

        assert result.name == "Bob Smith"
        assert result.email == "bob@company.com"

    @patch("src.services.extraction.get_groq_client")
    async def test_regex_supplies_phone(self, mock_get_client):
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            return_value=_make_groq_response(
                '{"name": "Carol White", "company": null, "role": null, '
                '"category": null, "context": null, '
                '"interaction_summary": null, "tasks": []}'
            )
        )
        mock_get_client.return_value = client

        result = await extract_contact_data("Carol White\n+1 415 555 0142")

        assert result.name == "Carol White"
        assert result.phone is not None

    @patch("src.services.extraction.get_groq_client")
    async def test_regex_supplies_website_from_bare_domain(self, mock_get_client):
        """Covers the extract_urls rewrite: business cards omit the scheme."""
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            return_value=_make_groq_response(
                '{"name": "Dana Lee", "company": "Globex", "role": null, '
                '"category": null, "context": null, '
                '"interaction_summary": null, "tasks": []}'
            )
        )
        mock_get_client.return_value = client

        result = await extract_contact_data("Dana Lee\nGlobex\nwww.globex.io")

        assert result.website == "https://globex.io"
