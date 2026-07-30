"""
Test: Search endpoint via HTTP API.

/api/search has TWO LLM boundaries, not one, and both must be stubbed:

  1. parse_query()  — a lightweight intent classifier that runs on EVERY query
  2. semantic_search_with_explanation() — reached only for the fts_search intent

Stubbing only the second is what made test_search_returns_matches issue a real
HTTP request to Groq and fail with a 401 on the fake key. The intent router was
added after this test was written, and the test was never updated.

Both are imported lazily inside the endpoint, so patching them at their defining
module works — a module-level `from ... import` would have required patching the
use site in src.api.web instead.

Behaviors:
  - "GET /api/search?q=... routes a deterministic intent without a second LLM call"
  - "GET /api/search?q=... returns semantic matches in the standard contact shape"
  - "GET /api/search requires a query"
"""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
class TestSearchEndpoint:
    @patch("src.services.semantic_search.semantic_search_with_explanation", new_callable=AsyncMock)
    @patch("src.services.query_parser.parse_query", new_callable=AsyncMock)
    async def test_search_returns_matches(self, mock_parse, mock_search, client, db, make_contact):
        """
        The fts_search path: intent router falls through to semantic search, and
        the result is serialized in the same contact shape every other intent uses.
        """
        contact = await make_contact(name="Searchable Alice", company="AliceCorp")

        # Force the fallback intent so the endpoint reaches semantic search.
        mock_parse.return_value = {
            "intent": "fts_search",
            "filters": {"query_text": "Alice"},
        }

        # The stub must return the REAL contact id.
        #
        # The endpoint maps LLM-returned ids back to Contact rows and
        # re-serializes them through _serialize_contacts_brief, so /api/search
        # returns one shape regardless of which intent fired. It previously
        # returned the richer internal dicts on this branch only, meaning the
        # response schema depended on which intent the LLM happened to pick.
        #
        # A fabricated id like "abc" therefore resolves to nothing and yields an
        # empty list — which the old assertion `len(body["contacts"]) >= 0` could
        # not detect, because that condition is true for every possible list.
        mock_search.return_value = {
            "matches": [{"id": contact.id, "name": "Searchable Alice"}],
            "explanation": "Name match",
        }

        resp = await client.get("/api/search?q=Alice")

        assert resp.status_code == 200
        body = resp.json()
        assert body["query"] == "Alice"
        assert body["explanation"] == "Name match"

        # A real assertion: the matched contact comes back, in the brief shape.
        assert len(body["contacts"]) == 1
        returned = body["contacts"][0]
        assert returned["id"] == contact.id
        assert returned["name"] == "Searchable Alice"
        assert returned["company"] == "AliceCorp"
        assert set(returned) == {"id", "name", "company", "role", "category"}

    @patch("src.services.semantic_search.semantic_search_with_explanation", new_callable=AsyncMock)
    @patch("src.services.query_parser.parse_query", new_callable=AsyncMock)
    async def test_deterministic_intent_skips_semantic_search(
        self, mock_parse, mock_search, client, db, make_contact
    ):
        """
        contact_lookup is answered with plain SQL. The point of the intent router
        is that a literal query does NOT pay for a second LLM call, so asserting
        semantic search was never invoked is asserting the actual feature.
        """
        contact = await make_contact(name="Eddie Deterministic", company="EddieCo")

        mock_parse.return_value = {
            "intent": "contact_lookup",
            "filters": {"name": "Eddie"},
        }

        resp = await client.get("/api/search?q=who is Eddie")

        assert resp.status_code == 200
        body = resp.json()
        assert body["intent"] == "contact_lookup"
        assert any(c["id"] == contact.id for c in body["contacts"])

        mock_search.assert_not_awaited()

    async def test_search_requires_query(self, client):
        resp = await client.get("/api/search")
        # FastAPI validates min_length=1
        assert resp.status_code == 422
