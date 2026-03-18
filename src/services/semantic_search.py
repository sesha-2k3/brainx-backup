"""
Semantic search using LLM to find relevant contacts.
"""

import json
import logging
from typing import Any

from src.config import get_settings
from src.services.groq_client import get_groq_client

logger = logging.getLogger(__name__)

# Constants
MAX_NOTES_LENGTH = 200
MAX_CONTEXT_LENGTH = 200
MAX_INTERACTIONS_LENGTH = 300
MAX_CONTACTS_FOR_SEARCH = 50


def _parse_llm_json(content: str) -> Any:
    """Parse JSON from LLM response, handling markdown code blocks."""
    content = content.strip()

    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first line (```json) and last line (```)
        content = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    return json.loads(content)


def _build_contact_context(contacts: list[dict]) -> str:
    """Build formatted context string from contacts for LLM."""
    context_parts = []

    for i, c in enumerate(contacts[:MAX_CONTACTS_FOR_SEARCH]):
        parts = [f"#{i + 1} {c.get('name', 'Unknown')}"]

        if c.get("company"):
            parts.append(f"({c['company']})")
        if c.get("role"):
            parts.append(f"[{c['role']}]")
        if c.get("category"):
            parts.append(f"<{c['category']}>")
        if c.get("notes"):
            parts.append(f"Notes: {c['notes'][:MAX_NOTES_LENGTH]}")
        if c.get("context"):
            parts.append(f"Context: {c['context'][:MAX_CONTEXT_LENGTH]}")
        if c.get("interactions"):
            parts.append(f"Interactions: {c['interactions'][:MAX_INTERACTIONS_LENGTH]}")

        context_parts.append(" | ".join(parts))

    return "\n".join(context_parts)


SEARCH_PROMPT = """You are a precise CRM search assistant. Return ONLY contacts that DIRECTLY match the query.

CONTACTS:
{context}

QUERY: "{query}"

STRICT RULES:
- Only return contacts where the query topic appears in their notes, context, or interactions
- Do NOT return contacts just because they share a category (e.g., don't return all "investors" for a specific topic)
- If asking "who discussed X", only return contacts whose interactions mention X
- If asking "who is X", only return contacts named X
- Be STRICT - fewer accurate results is better than many irrelevant ones
- If no contacts directly match, return empty array

Respond with JSON only:
{{
  "matches": [1, 2],
  "explanation": "Why these specific contacts match"
}}

JSON:"""


async def semantic_search_with_explanation(query: str, contacts: list[dict]) -> dict:
    """
    Semantic search that returns only highly relevant matches.

    Args:
        query: Natural language search query
        contacts: List of contact dictionaries to search through

    Returns:
        Dict with 'matches' (list of matching contacts) and 'explanation' (str)
    """
    if not contacts:
        return {"matches": [], "explanation": "No contacts in database."}

    if not query.strip():
        return {"matches": [], "explanation": "Empty search query."}

    context = _build_contact_context(contacts)
    prompt = SEARCH_PROMPT.format(context=context, query=query)

    settings = get_settings()
    client = get_groq_client()

    try:
        response = await client.chat.completions.create(
            model=settings.groq_llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=300,
        )

        content = response.choices[0].message.content.strip()
        logger.info(f"Search query: {query}")
        logger.debug(f"LLM response: {content}")

        # Parse JSON (handles both raw JSON and markdown-wrapped)
        result = _parse_llm_json(content)

        # Convert 1-based indices to actual contacts
        matches = []
        for idx in result.get("matches", []):
            actual_idx = idx - 1  # LLM uses 1-based indexing
            if 0 <= actual_idx < len(contacts):
                matches.append(contacts[actual_idx])
            else:
                logger.warning(f"Invalid contact index from LLM: {idx}")

        return {
            "matches": matches,
            "explanation": result.get("explanation", ""),
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        return {"matches": [], "explanation": "Failed to parse search results."}

    except Exception as e:
        logger.error(f"Semantic search error: {e}", exc_info=True)
        return {"matches": [], "explanation": "Search failed."}
