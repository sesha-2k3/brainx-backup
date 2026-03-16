"""
Test: Query parser service.

_resolve_dates and format_search_results are pure logic → zero doubles.
parse_query calls the Groq LLM → STUB it (foreign system).

Behaviors:
  - "_resolve_dates resolves relative date tokens to ISO strings"
  - "parse_query classifies intent and extracts filters from LLM"
  - "parse_query falls back to fts_search on invalid JSON"
  - "format_search_results produces human-readable text"
  - "format_search_results handles empty results"
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.query_parser import (
    _resolve_dates,
    format_search_results,
    parse_query,
)


# ---------------------------------------------------------------------------
# Pure logic: _resolve_dates (zero doubles)
# ---------------------------------------------------------------------------
class TestResolveDates:

    def test_30_days_ago(self):
        filters = {"date_range": {"start": "30_days_ago", "end": "today"}}
        result = _resolve_dates(filters)
        # Start should be an ISO date string
        assert "T" in result["date_range"]["start"]
        assert "T" in result["date_range"]["end"]

    def test_7_days_ago(self):
        filters = {"date_range": {"start": "7_days_ago", "end": "today"}}
        result = _resolve_dates(filters)
        assert "T" in result["date_range"]["start"]

    def test_this_month(self):
        filters = {"date_range": {"start": "this_month", "end": "today"}}
        result = _resolve_dates(filters)
        # Start should be the 1st of the month
        parsed = datetime.fromisoformat(result["date_range"]["start"])
        assert parsed.day == 1

    def test_due_date_today(self):
        filters = {"due_date": "today"}
        result = _resolve_dates(filters)
        assert "due_by" in result

    def test_due_date_this_week(self):
        filters = {"due_date": "this_week"}
        result = _resolve_dates(filters)
        assert "due_by" in result

    def test_due_date_overdue(self):
        filters = {"due_date": "overdue"}
        result = _resolve_dates(filters)
        assert result["overdue"] is True
        assert "due_by" in result

    def test_no_dates_passes_through(self):
        filters = {"name": "Eddie"}
        result = _resolve_dates(filters)
        assert result == {"name": "Eddie"}

    def test_empty_filters(self):
        result = _resolve_dates({})
        assert result == {}


# ---------------------------------------------------------------------------
# Foreign boundary: parse_query (stubs Groq LLM)
# ---------------------------------------------------------------------------
def _make_groq_response(json_str):
    resp = MagicMock()
    resp.choices = [MagicMock(message=MagicMock(content=json_str))]
    return resp


@pytest.mark.asyncio
class TestParseQuery:

    @patch("src.services.query_parser.get_groq_client")
    async def test_contact_lookup(self, mock_get_client):
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            return_value=_make_groq_response(
                '{"intent": "contact_lookup", "filters": {"name": "Eddie"}}'
            )
        )
        mock_get_client.return_value = client

        result = await parse_query("Who is Eddie?")
        assert result["intent"] == "contact_lookup"
        assert result["filters"]["name"] == "Eddie"

    @patch("src.services.query_parser.get_groq_client")
    async def test_task_query_with_date_resolution(self, mock_get_client):
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            return_value=_make_groq_response(
                '{"intent": "task_query", "filters": {"due_date": "today"}}'
            )
        )
        mock_get_client.return_value = client

        result = await parse_query("What's due today?")
        assert result["intent"] == "task_query"
        # _resolve_dates should have added due_by
        assert "due_by" in result["filters"]

    @patch("src.services.query_parser.get_groq_client")
    async def test_markdown_wrapped_json(self, mock_get_client):
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            return_value=_make_groq_response(
                '```json\n{"intent": "fts_search", "filters": {"query_text": "AI"}}\n```'
            )
        )
        mock_get_client.return_value = client

        result = await parse_query("Search for AI")
        assert result["intent"] == "fts_search"

    @patch("src.services.query_parser.get_groq_client")
    async def test_invalid_json_falls_back_to_fts(self, mock_get_client):
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            return_value=_make_groq_response("this is not json")
        )
        mock_get_client.return_value = client

        result = await parse_query("something weird")
        assert result["intent"] == "fts_search"
        assert result["filters"]["query_text"] == "something weird"


# ---------------------------------------------------------------------------
# Pure logic: format_search_results (uses simple namespace objects)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestFormatSearchResults:

    async def test_formats_contacts(self):
        contacts = [
            SimpleNamespace(name="Alice", company="Acme", category="investor"),
            SimpleNamespace(name="Bob", company=None, category=None),
        ]
        result = await format_search_results(
            {"contacts": contacts, "interactions": [], "tasks": []},
            "test query",
        )
        assert "Found 2 contact(s)" in result
        assert "Alice" in result
        assert "Acme" in result
        assert "investor" in result
        assert "Bob" in result

    async def test_formats_interactions(self):
        interactions = [
            SimpleNamespace(
                occurred_at=datetime(2025, 3, 1, tzinfo=timezone.utc),
                summary="Discussed partnership deal with Acme",
            ),
        ]
        result = await format_search_results(
            {"contacts": [], "interactions": interactions, "tasks": []},
            "test",
        )
        assert "Found 1 interaction(s)" in result
        assert "2025-03-01" in result

    async def test_formats_tasks(self):
        tasks = [
            SimpleNamespace(
                title="Follow up with Jane",
                due_date=datetime(2025, 4, 15, tzinfo=timezone.utc),
            ),
        ]
        result = await format_search_results(
            {"contacts": [], "interactions": [], "tasks": tasks},
            "test",
        )
        assert "Found 1 task(s)" in result
        assert "Follow up with Jane" in result

    async def test_formats_tasks_with_no_due_date(self):
        tasks = [SimpleNamespace(title="No deadline task", due_date=None)]
        result = await format_search_results(
            {"contacts": [], "interactions": [], "tasks": tasks},
            "test",
        )
        assert "No due date" in result

    async def test_empty_results(self):
        result = await format_search_results(
            {"contacts": [], "interactions": [], "tasks": []},
            "missing person",
        )
        assert "No results found for: missing person" in result
