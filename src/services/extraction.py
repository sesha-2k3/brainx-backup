# Service: LLM-based extraction of contact and interaction data

import json
import logging
from typing import Optional

from groq import AsyncGroq

from src.config import get_settings
from src.schemas.contacts import ExtractedContactData

logger = logging.getLogger(__name__)
settings = get_settings()

client = AsyncGroq(api_key=settings.groq_api_key)

EXTRACTION_PROMPT = """You are extracting contact and interaction information from a voice note or text message.

Extract the following fields if present. Return ONLY a JSON object with these keys:
- name: Person's full name
- email: Email address
- phone: Phone number
- company: Company or organization name
- role: Job title or role
- category: One of: investor, client, partner, friend, family, colleague, other
- context: How/where they met or relationship context
- interaction_summary: Brief summary of what was discussed or noted
- follow_up: Any follow-up action mentioned
- follow_up_date: Follow-up date if mentioned (ISO format YYYY-MM-DD or relative like "next week")

If a field is not mentioned or unclear, set it to null.
Be concise in summaries. Extract exact values for name, email, phone.

TEXT TO EXTRACT FROM:
{text}

Respond with ONLY the JSON object, no markdown or explanation."""


async def extract_contact_data(text: str) -> ExtractedContactData:
    """
    Extract structured contact data from free-form text using LLM.
    """
    logger.info(f"Extracting data from text: {len(text)} chars")
    
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
