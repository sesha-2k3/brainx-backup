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
        assert result.email == "alice@example.com"
        assert len(result.tasks) == 1
        assert result.tasks[0].title == "Follow up"

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
        client.chat.completions.create = AsyncMock(
            return_value=_make_groq_response("garbage")
        )
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
            return_value=_make_groq_response(
                '{"matches": [1], "explanation": "Name match"}'
            )
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
        client.chat.completions.create = AsyncMock(
            return_value=_make_groq_response("not json")
        )
        mock_get_client.return_value = client

        result = await semantic_search_with_explanation(
            "test", [{"name": "X"}]
        )
        assert result["matches"] == []
