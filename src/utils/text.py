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


# Domains a business card or a pasted note will realistically carry. This is an
# allowlist rather than a generic `\.[a-z]{2,}` rule on purpose: the loose
# version happily reads "notes.txt", "report.pdf", "app.js" and "e.g." as
# websites. Ambiguous TLDs that collide with common file extensions (.sh, .py,
# .rs, .md) are deliberately omitted - a missed website is recoverable by hand,
# a garbage one silently pollutes the contact record.
_URL_TLDS = (
    # generic
    "com|net|org|edu|gov|mil|int|info|biz|name|pro|xyz|online|site|website|"
    "store|shop|tech|dev|app|cloud|digital|agency|studio|design|media|news|"
    "blog|wiki|email|group|team|works|solutions|systems|consulting|capital|"
    "ventures|partners|finance|health|law|academy|institute|foundation|"
    # common ccTLD / vanity
    "io|ai|co|me|tv|cc|gg|ly|to|us|uk|ca|au|nz|de|fr|es|it|nl|se|no|dk|fi|"
    "pl|pt|gr|ie|be|at|ch|cz|ro|hu|ru|ua|tr|il|ae|sa|za|ng|ke|eg|in|pk|bd|"
    "lk|np|cn|jp|kr|tw|hk|sg|my|th|vn|ph|id|br|mx|ar|cl|co\\.uk|co\\.in|"
    "com\\.au|com\\.br|co\\.za|co\\.jp|co\\.nz"
)

_URL_PATTERN = re.compile(
    r"""
    (?<![\w@.\-])                       # not mid-word, and not the domain half of an email
    (?:(?P<scheme>https?://)|www\.)?    # optional scheme, or a bare www.
    (?P<host>
        (?:[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?\.)+   # one or more dot-separated labels
        (?:"""
    + _URL_TLDS
    + r""")
    )
    \b
    (?P<path>/[^\s<>"'{}|\\^`\[\]]*)?   # optional path/query
    """,
    re.IGNORECASE | re.VERBOSE,
)


def extract_urls(text: str) -> list[str]:
    """
    Extract website URLs from free text, including scheme-less ones.

    Business cards and pasted notes overwhelmingly write "acme.com" or
    "www.acme.com" rather than "https://acme.com", so requiring a scheme (as
    this function used to) meant the website field almost never populated.

    Returned URLs are normalized to include a scheme, so the value is directly
    usable as an href. Email addresses are excluded - their domain half would
    otherwise match. Order is preserved and duplicates are removed.
    """
    if not text:
        return []

    # Strip emails first so "sam@acme.com" doesn't yield "acme.com" as a site.
    # (An email is a strong signal on a business card, but it isn't a website.)
    without_emails = re.sub(r"[\w.\-+]+@[\w.\-]+\.\w+", " ", text)

    seen: set[str] = set()
    results: list[str] = []

    for match in _URL_PATTERN.finditer(without_emails):
        host = match.group("host")
        path = match.group("path") or ""
        scheme = match.group("scheme") or "https://"

        # Rebuild from parts so "www.acme.com" and "acme.com" don't both need
        # separate handling, and so the trailing sentence punctuation that
        # \b happily includes in a path gets trimmed.
        path = path.rstrip(".,;:!?)")
        url = f"{scheme}{host}{path}"

        key = url.lower()
        if key not in seen:
            seen.add(key)
            results.append(url)

    return results


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
