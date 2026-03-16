# Utils: Phone number normalization

import re

import phonenumbers


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
