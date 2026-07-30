"""
Service: Hybrid extraction of contact and interaction data.

Deterministic first, LLM only for what regex genuinely can't do:
  - email / phone   -> regex only, LLM is never asked for these anymore
  - category        -> keyword match first; LLM only used as a fallback
                        guess, and even then clamped to the enum
  - name / company / role / context / interaction_summary / tasks
                        -> LLM (open-ended language understanding, no
                        deterministic substitute)
  - task due_date    -> LLM extracts the phrase, parse_relative_date()
                        resolves it downstream (unchanged, already correct)
"""

import asyncio
import json
import logging

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import get_settings
from src.schemas.contacts import ExtractedContactData
from src.services.groq_client import get_groq_client
from src.utils.category import clamp_category, match_category_keywords
from src.utils.phone import extract_phones
from src.utils.text import extract_emails, extract_urls, parse_llm_json

logger = logging.getLogger(__name__)

MAX_EXTRACTION_TEXT_LENGTH = 6_000
EXTRACTION_TIMEOUT = 30.0

# NOTE: email, phone, and category are intentionally absent from what we ask
# the LLM to find. Email/phone come from regex (extract_emails / extract_phones)
# run on the *full* untruncated text before this prompt is even built - the
# LLM would just be re-deriving something a pattern already gets exactly
# right, at the cost of tokens, latency, and a small hallucination surface.
# Category is asked for here only as a fallback for when a deterministic
# keyword match (match_category_keywords) doesn't find one - its output is
# clamped against the enum afterwards either way.
EXTRACTION_PROMPT = """Extract contact information and ALL tasks/follow-ups from this text.

TEXT:
{text}

Return a JSON object with these fields:
- name: Full name of the person
- company: Company/organization name (or null)
- role: Job title/role (or null)
- category: Best guess, one of: investor, client, partner, friend, family, colleague, other (or null if unclear)
- context: How/where you met this person (or null)
- interaction_summary: Brief summary of the conversation/interaction (or null)
- tasks: Array of tasks/follow-ups extracted. Each task has:
  - title: What needs to be done
  - due_date: When (use relative terms like "tomorrow", "next week", "in 3 days", or null)

Example output:
{{
  "name": "John Smith",
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
    Extract structured contact data from free-form text.

    Deterministic (regex) fields are pulled from the full text first. The
    LLM is only used for the fields that genuinely require open-ended
    language understanding, and only sees a possibly-truncated copy of the
    text for that part.

    Raises:
        ExtractionError: If extraction fails after retries
    """
    settings = get_settings()

    # --- Deterministic pass: runs on the full, untruncated text --------------
    emails = extract_emails(text)
    phones = extract_phones(text)
    urls = extract_urls(text)
    keyword_category = match_category_keywords(text)

    # --- LLM pass: only for name / company / role / context / summary / tasks,
    # and category as a fallback guess if no keyword matched -----------------
    llm_text = text
    if len(text) > MAX_EXTRACTION_TEXT_LENGTH:
        logger.warning(f"Text truncated from {len(text)} to {MAX_EXTRACTION_TEXT_LENGTH} chars")
        llm_text = text[:MAX_EXTRACTION_TEXT_LENGTH]

    logger.info(f"Extracting data from text: {len(llm_text)} chars (LLM portion)")

    client = get_groq_client()

    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=settings.groq_llm_model,
                messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(text=llm_text)}],
                temperature=0.1,
                max_tokens=400,  # was 500 - prompt shrank, response shrinks too
            ),
            timeout=EXTRACTION_TIMEOUT,
        )
    except TimeoutError:
        logger.warning("Extraction timed out, will retry...")
        raise  # Reraise to trigger retry

    content = response.choices[0].message.content.strip()

    try:
        data = parse_llm_json(content)
        extracted = ExtractedContactData(**data)

        # Deterministic fields always win - the LLM was never even asked, so
        # there's nothing to reconcile, just attach the regex results.
        #
        # The unconditional None is deliberate, not an oversight. EXTRACTION_PROMPT
        # does not request email, phone or website at all (see the NOTE above it),
        # so anything the model volunteers for those fields is unrequested output.
        # Normalizing to None guarantees the invariant "these three fields come
        # from regex on the full untruncated text, or they are empty" and closes
        # the hallucination surface that asking would open.
        #
        # Consequence worth knowing: nothing recovers a contact detail the regex
        # cannot match - "her email is alice at example dot com", or OCR that
        # renders "@" as "(a)". That is a conscious recall-for-determinism trade,
        # not a defect. Changing it means asking the LLM for these fields as an
        # explicit fallback and merging regex-first, which is a design decision
        # about token cost and trust, not a bug fix.
        extracted.email = emails[0] if emails else None
        extracted.phone = phones[0] if phones else None
        extracted.website = urls[0] if urls else None

        # Category: trust the keyword match over anything the LLM guessed.
        # If there was no keyword match, fall back to the LLM's guess - but
        # clamp it to the enum so a hallucinated value can never land in the DB.
        if keyword_category is not None:
            extracted.category = keyword_category.value
        else:
            extracted.category = clamp_category(extracted.category)

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
    except (TimeoutError, ExtractionError) as e:
        logger.error(f"Extraction failed after retries: {e}")
        return ExtractedContactData()


# TODO: Add these in future releases!


async def summarize_interaction(text: str, max_length: int = 200) -> str:
    """
    Generate a concise summary of an interaction.
    """
    prompt = f"""Summarize this interaction in {max_length} characters or less.
    Be concise and capture the key points.

    TEXT:
    {text}

    SUMMARY:"""

    settings = get_settings()
    client = get_groq_client()

    response = await client.chat.completions.create(
        model=settings.groq_llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=100,
    )

    return response.choices[0].message.content.strip()


# TODO: Add these in future releases!


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

    settings = get_settings()
    client = get_groq_client()

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
