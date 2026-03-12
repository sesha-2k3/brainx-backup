# Service: LLM-based extraction of contact and interaction data

import asyncio
import json
import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.config import get_settings
from src.schemas.contacts import ExtractedContactData
from src.services.groq_client import get_groq_client
from src.utils.text import parse_llm_json


logger = logging.getLogger(__name__)

MAX_EXTRACTION_TEXT_LENGTH = 6_000
EXTRACTION_TIMEOUT = 30.0
EXTRACTION_PROMPT = """Extract contact information and ALL tasks/follow-ups from this text.

TEXT:
{text}

Return a JSON object with these fields:
- name: Full name of the person
- email: Email address (or null)
- phone: Phone number (or null)
- company: Company/organization name (or null)
- role: Job title/role (or null)
- category: One of: investor, client, partner, friend, family, colleague, other (or null)
- context: How/where you met this person (or null)
- interaction_summary: Brief summary of the conversation/interaction (or null)
- tasks: Array of tasks/follow-ups extracted. Each task has:
  - title: What needs to be done
  - due_date: When (use relative terms like "tomorrow", "next week", "in 3 days", or null)

Example output:
{{
  "name": "John Smith",
  "email": "john@acme.com",
  "company": "Acme Corp",
  "role": "VP Sales",
  "category": "client",
  "context": "Met at tech conference",
  "interaction_summary": "Discussed partnership opportunity",
  "tasks": [
    {{"title": "Send proposal to John", "due_date": "next week"}},
    {{"title": "Schedule follow-up call", "due_date": "in 3 days"}}
  ]
}}

JSON only, no explanation:"""

class ExtractionError(Exception):
    """Raised when contact extraction fails."""
    pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((asyncio.TimeoutError, ExtractionError)),
    reraise=True,
)
async def extract_contact_data(text: str) -> ExtractedContactData:
    """
    Extract structured contact data from free-form text using LLM.
    
    Raises:
        ExtractionError: If extraction fails after retries
    """
    settings = get_settings()
    
    # Limit input size
    if len(text) > MAX_EXTRACTION_TEXT_LENGTH:
        logger.warning(f"Text truncated from {len(text)} to {MAX_EXTRACTION_TEXT_LENGTH} chars")
        text = text[:MAX_EXTRACTION_TEXT_LENGTH]
    
    logger.info(f"Extracting data from text: {len(text)} chars")
    
    client = get_groq_client()
    
    # Call LLM with timeout
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=settings.groq_llm_model,
                messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(text=text)}],
                temperature=0.1,
                max_tokens=500,
            ),
            timeout=EXTRACTION_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.warning("Extraction timed out, will retry...")
        raise  # Reraise to trigger retry
    
    content = response.choices[0].message.content.strip()
    
    # Parse JSON response
    try:
        data = parse_llm_json(content)
        extracted = ExtractedContactData(**data)
        
        if not extracted.name:
            raise ExtractionError("No name extracted from text")
        
        logger.info(f"Extracted contact: {extracted.name}")
        return extracted
    
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM response, will retry: {e}")
        raise ExtractionError(f"Invalid JSON response: {e}") from e
    
    except ValueError as e:
        logger.warning(f"Invalid extracted data, will retry: {e}")
        raise ExtractionError(f"Validation failed: {e}") from e

async def extract_contact_data_safe(text: str) -> ExtractedContactData:
    """
    Safe wrapper that returns empty data instead of raising.
    Use this in endpoints where you want graceful degradation.
    """
    try:
        return await extract_contact_data(text)
    except (ExtractionError, asyncio.TimeoutError) as e:
        logger.error(f"Extraction failed after retries: {e}")
        return ExtractedContactData()

async def summarize_interaction(text: str, max_length: int = 200) -> str:
    """
    Generate a concise summary of an interaction.
    """
    prompt = f"""Summarize this interaction in {max_length} characters or less. 
Be concise and capture the key points.

TEXT:
{text}

SUMMARY:"""

    response = await client.chat.completions.create(
        model=settings.groq_llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=100,
    )
    
    return response.choices[0].message.content.strip()


async def detect_intent(text: str) -> dict:
    """
    Detect user intent from a message (query, add contact, task, etc.)
    Returns dict with 'intent' and 'entities' keys.
    """
    prompt = """Classify this message intent. Return JSON with:
- intent: one of [add_contact, add_task, search_contact, search_interaction, list_tasks, help, other]
- entities: relevant extracted entities (name, date, query terms, etc.)

MESSAGE:
{text}

JSON:"""

    response = await client.chat.completions.create(
        model=settings.groq_llm_model,
        messages=[{"role": "user", "content": prompt.format(text=text)}],
        temperature=0.1,
        max_tokens=150,
    )
    
    content = response.choices[0].message.content.strip()
    
    try:
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except json.JSONDecodeError:
        return {"intent": "other", "entities": {}}
