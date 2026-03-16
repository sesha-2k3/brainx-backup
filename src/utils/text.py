# Utils: Text cleaning and processing

import json
import re
from typing import Any


def clean_text(text: str | None) -> str:
    """
    Clean and normalize text.
    """
    if not text:
        return ""

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def truncate(text: str | None, max_length: int = 200, suffix: str = "...") -> str:
    """
    Truncate text to max length, adding suffix if truncated.
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)].rsplit(" ", 1)[0] + suffix


def extract_emails(text: str) -> list[str]:
    """
    Extract all email addresses from text.
    """
    pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
    return re.findall(pattern, text.lower())


def extract_urls(text: str) -> list[str]:
    """
    Extract all URLs from text.
    """
    pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(pattern, text)


def normalize_name(name: str | None) -> str:
    """
    Normalize a person's name (title case, clean whitespace).
    """
    if not name:
        return ""

    # Clean whitespace
    name = clean_text(name)

    # Title case
    name = name.title()

    # Fix common issues with title case
    name = re.sub(r"'S\b", "'s", name)  # O'Brien's -> O'Brien's
    name = re.sub(r"\bMc(\w)", lambda m: f"Mc{m.group(1).upper()}", name)  # Mcdonald -> McDonald
    name = re.sub(
        r"\bMac(\w)", lambda m: f"Mac{m.group(1).upper()}", name
    )  # Macdonald -> MacDonald

    return name


def build_search_text(*fields: str | None) -> str:
    """
    Build a searchable text string from multiple fields.
    """
    parts = [clean_text(f) for f in fields if f]
    return " ".join(parts).lower()


def escape_like(value: str) -> str:
    r"""
    Escape special characters for LIKE/ILIKE queries.

    Special characters in LIKE:
    - % matches any sequence of characters
    - _ matches any single character
    - \ is the escape character
    """
    return (
        value.replace("\\", "\\\\")  # Escape backslash first
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def parse_llm_json(content: str) -> Any:
    """Parse JSON from LLM response, handling markdown code blocks."""
    content = content.strip()

    # Remove markdown code blocks
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first and last lines (``` markers)
        content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        # Remove language identifier
        if content.startswith("json"):
            content = content[4:].strip()

    return json.loads(content)
