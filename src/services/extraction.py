# Service: LLM-based extraction of contact and interaction data

import json
import logging
from typing import Optional
from functools import lru_cache
from groq import AsyncGroq
from src.config import get_settings
from src.schemas.contacts import ExtractedContactData

logger = logging.getLogger(__name__)
settings = get_settings()

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

@lru_cache()
def get_groq_client() -> AsyncGroq:
    """Lazy initialization of Groq client."""
    settings = get_settings()
    return AsyncGroq(api_key=settings.groq_api_key)

async def extract_contact_data(text: str) -> ExtractedContactData:
    """
    Extract structured contact data from free-form text using LLM.
    """
    logger.info(f"Extracting data from text: {len(text)} chars")
    
    client = get_groq_client() # Lazy initialization of Groq client
    response = await client.chat.completions.create(
        model=settings.groq_llm_model,
        messages=[
            {"role": "user", "content": EXTRACTION_PROMPT.format(text=text)}
        ],
        temperature=0.1,
        max_tokens=500,
    )
    
    content = response.choices[0].message.content.strip()
    
    # Parse JSON response
    try:
        # Handle potential markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        data = json.loads(content)
        extracted = ExtractedContactData(**data)
        logger.info(f"Extracted contact: {extracted.name}")
        return extracted
    
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse extraction response: {e}")
        logger.debug(f"Raw response: {content}")
        # Return empty extraction
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
