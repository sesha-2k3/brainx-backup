# Service: Natural language query parsing using LLM
"""
Purpose: Natural language query router that classifies user search intent and extracts structured filters using LLM.

Status: Now wired into GET /api/search (see src/api/web.py). This replaces the
        old behavior of always loading up to 100 contacts and calling the
        heavier semantic_search_with_explanation() LLM call for every query.

        parse_query() below is still an LLM call - classifying intent isn't
        something regex can do - but it's a much lighter one (~200 tokens vs
        a full contact dump), and its output routes most queries straight to
        SQL. semantic_search_with_explanation() is only reached now for the
        `fts_search` fallback intent (genuinely fuzzy/unclassifiable queries).

Functions:

| Function | Description |
|----------|-------------|
| `parse_query(query)` | Sends query to Groq LLM, returns `{intent, filters}` |
| `_resolve_dates(filters)` | Converts relative dates (`"today"`, `"30_days_ago"`, or any phrase parse_relative_date understands) to ISO strings |
| `format_search_results(results, query)` | Formats results as human-readable text (for WhatsApp) |

**Intents supported:**
- `contact_lookup` — "Who is Eddie?"
- `filtered_list` — "Show me all investors"
- `task_query` — "What's due today?"
- `interaction_search` — "What did we discuss with BCBS?"
- `fts_search` — Fallback for general queries
"""

import json
import logging
from datetime import UTC, datetime, timedelta

from src.config import get_settings
from src.services.groq_client import get_groq_client
from src.utils.dates import parse_relative_date

logger = logging.getLogger(__name__)

QUERY_PARSER_PROMPT = """Parse this search query into a structured format.

Return JSON with:
- intent: one of [contact_lookup, filtered_list, task_query, interaction_search, fts_search]
- filters: object with applicable filters

Intent meanings:
- contact_lookup: Looking for a specific person by name ("Who is Eddie?")
- filtered_list: List contacts by category/criteria ("Show me all investors")
- task_query: Looking for tasks/follow-ups ("What's due today?")
- interaction_search: Searching past interactions ("What did we discuss with BCBS?")
- fts_search: General search across everything

Possible filters:
- name: person name to search
- company: company name
- category: investor, client, partner, friend, family, colleague
- date_range: object with start and end ISO dates
- query_text: text to search for
- due_date: for tasks (today, this_week, overdue)

Examples:
"Who is Eddie?" -> {{"intent": "contact_lookup", "filters": {{"name": "Eddie"}}}}
"Investors I met last 30 days" -> {{"intent": "filtered_list", "filters": {{"category": "investor", "date_range": {{"start": "30_days_ago", "end": "today"}}}}}}
"Follow-ups due today" -> {{"intent": "task_query", "filters": {{"due_date": "today"}}}}
"What did we discuss with BCBS?" -> {{"intent": "interaction_search", "filters": {{"company": "BCBS"}}}}

Today's date: {today}

QUERY: {query}

JSON:"""


async def parse_query(query: str) -> dict:
    """
    Parse a natural language query into structured search parameters.
    """
    logger.info(f"Parsing query: {query}")

    settings = get_settings()
    client = get_groq_client()

    today = datetime.now(UTC).strftime("%Y-%m-%d")

    response = await client.chat.completions.create(
        model=settings.groq_llm_model,
        messages=[
            {"role": "user", "content": QUERY_PARSER_PROMPT.format(query=query, today=today)}
        ],
        temperature=0.1,
        max_tokens=200,
    )

    content = response.choices[0].message.content.strip()

    try:
        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        parsed = json.loads(content)

        # Resolve relative dates
        parsed["filters"] = _resolve_dates(parsed.get("filters", {}))

        logger.info(f"Parsed intent: {parsed.get('intent')}, filters: {parsed.get('filters')}")
        return parsed

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse query response: {e}")
        # Fall back to FTS search
        return {"intent": "fts_search", "filters": {"query_text": query}}


def _resolve_dates(filters: dict) -> dict:
    """
    Resolve relative date strings to actual dates.

    Handles the common phrases explicitly, then falls back to
    parse_relative_date() (already used elsewhere for task due-dates) for
    anything else the LLM returns - so an unusual phrase like "next Friday"
    still resolves deterministically instead of being silently dropped.
    """
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    # Handle date_range
    if "date_range" in filters:
        date_range = filters["date_range"]

        start = date_range.get("start")
        if start == "30_days_ago":
            date_range["start"] = (today - timedelta(days=30)).isoformat()
        elif start == "7_days_ago":
            date_range["start"] = (today - timedelta(days=7)).isoformat()
        elif start == "this_month":
            date_range["start"] = today.replace(day=1).isoformat()
        elif start and start not in ("today",):
            resolved = parse_relative_date(start)
            if resolved:
                date_range["start"] = resolved.isoformat()

        end = date_range.get("end")
        if end == "today":
            date_range["end"] = today.isoformat()
        elif end and end != date_range.get("start"):
            resolved = parse_relative_date(end)
            if resolved:
                date_range["end"] = resolved.isoformat()

        filters["date_range"] = date_range

    # Handle due_date for tasks
    if "due_date" in filters:
        due = filters["due_date"]
        if due == "today":
            filters["due_by"] = today.isoformat()
        elif due == "this_week":
            # End of week (Sunday)
            days_until_sunday = 6 - today.weekday()
            filters["due_by"] = (today + timedelta(days=days_until_sunday)).isoformat()
        elif due == "overdue":
            filters["due_by"] = today.isoformat()
            filters["overdue"] = True
        else:
            resolved = parse_relative_date(due)
            if resolved:
                filters["due_by"] = resolved.isoformat()

    return filters


async def format_search_results(results: dict, query: str) -> str:
    """
    Format search results into a human-readable response.
    """
    contacts = results.get("contacts", [])
    interactions = results.get("interactions", [])
    tasks = results.get("tasks", [])

    parts = []

    if contacts:
        parts.append(f"Found {len(contacts)} contact(s):")
        for c in contacts[:5]:
            line = f"- {c.name}"
            if c.company:
                line += f" ({c.company})"
            if c.category:
                line += f" [{c.category}]"
            parts.append(line)

    if interactions:
        parts.append(f"\nFound {len(interactions)} interaction(s):")
        for i in interactions[:5]:
            date_str = i.occurred_at.strftime("%Y-%m-%d")
            parts.append(f"- {date_str}: {i.summary[:100]}")

    if tasks:
        parts.append(f"\nFound {len(tasks)} task(s):")
        for t in tasks[:5]:
            due = t.due_date.strftime("%Y-%m-%d") if t.due_date else "No due date"
            parts.append(f"- {t.title} (Due: {due})")

    if not any([contacts, interactions, tasks]):
        parts.append(f"No results found for: {query}")

    return "\n".join(parts)
