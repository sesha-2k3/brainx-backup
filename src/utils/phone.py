# Utils: Phone number normalization

import re

import phonenumbers

# Loose candidate pattern for scanning free text (business cards, pasted notes,
# voice transcripts). This is intentionally permissive - normalize_phone() and
# the digit-count check below do the real validation. Kept in one place so
# extraction.py and ocr.py don't each maintain their own copy.
_PHONE_CANDIDATE_PATTERN = re.compile(
    r"[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}"
)

# Below this many digits, a "phone-shaped" match is almost always something
# else (a year, a zip code, part of an address) - filter it out before we
# even try to normalize it.
_MIN_PHONE_DIGITS = 7


def normalize_phone(phone: str | None, default_region: str = "US") -> str | None:
    """
    Normalize a phone number to E.164 format.
    Returns None if invalid.
    """
    if not phone:
        return None

    # Remove common separators
    cleaned = re.sub(r"[\s\-\.\(\)]", "", phone)

    try:
        parsed = phonenumbers.parse(cleaned, default_region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass

    # Fall back to basic cleaning if parsing fails
    digits_only = re.sub(r"[^\d+]", "", phone)
    if len(digits_only) >= 10:
        return digits_only

    return None


def extract_phones(text: str, default_region: str = "US") -> list[str]:
    """
    Find and normalize phone numbers anywhere in free-form text.

    Deterministic replacement for asking an LLM to find a phone number.
    Returns normalized (E.164 where possible) numbers, in the order they
    appear, with duplicates removed.
    """
    if not text:
        return []

    seen: set[str] = set()
    results: list[str] = []

    for candidate in _PHONE_CANDIDATE_PATTERN.findall(text):
        digit_count = len(re.sub(r"[^\d]", "", candidate))
        if digit_count < _MIN_PHONE_DIGITS:
            continue

        normalized = normalize_phone(candidate, default_region=default_region)
        if normalized and normalized not in seen:
            seen.add(normalized)
            results.append(normalized)

    return results


def format_phone_display(phone: str | None, region: str = "US") -> str | None:
    """
    Format a phone number for display.
    """
    if not phone:
        return None

    try:
        parsed = phonenumbers.parse(phone, region)
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
    except phonenumbers.NumberParseException:
        return phone
