"""
Schemas: reusable validated field types.

These exist so a validation rule is defined once and applied to every schema
that needs it, rather than being re-implemented per endpoint. Task due dates
previously demonstrated the failure mode: POST took a typed datetime while
PATCH took a string and parsed relative phrases, so "tomorrow" worked on one
verb and silently failed on the other.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BeforeValidator

from src.schemas.contact_category_enums import ContactCategory
from src.utils.dates import ensure_aware, parse_relative_date

_VALID_CATEGORIES = ", ".join(c.value for c in ContactCategory)


def _validate_category(value: object) -> str | None:
    """
    Accept a contact category, case- and whitespace-insensitively.

    Deliberately STRICT: an unrecognized value raises, which FastAPI surfaces
    as a 422 naming the valid options.

    This is the opposite policy from clamp_category(), and the difference is
    intentional. clamp_category() maps unknown values to None and is used on
    the extraction path, where input comes from an LLM and must never hard-fail
    a user's capture. This validator is used on the paths where a human or an
    API client typed the value explicitly - there, silently discarding it means
    the caller believes they set a category and never finds out they didn't.

    Explicit input is validated. Inferred input is clamped.
    """
    if value is None:
        return None

    if isinstance(value, ContactCategory):
        return value.value

    if not isinstance(value, str):
        raise ValueError(f"Category must be a string, got {type(value).__name__}")

    normalized = value.strip().lower()
    if not normalized:
        # Treat "" as "not provided" rather than as an invalid category, so an
        # untouched form field doesn't produce a validation error.
        return None

    try:
        return ContactCategory(normalized).value
    except ValueError:
        raise ValueError(
            f"'{value}' is not a valid category. Valid options: {_VALID_CATEGORIES}"
        ) from None


def _validate_flexible_datetime(value: object) -> datetime | None:
    """
    Accept a datetime, an ISO 8601 string, or a relative phrase ("tomorrow",
    "next friday", "in 3 days"). Always returns a timezone-aware datetime.

    Precision is preserved as given: an explicit datetime or ISO string keeps
    its time component, while a relative phrase resolves to midnight because
    that is all the phrase specifies. ISO parsing is attempted BEFORE
    parse_relative_date() for exactly this reason - parse_relative_date()
    normalizes to midnight, which is correct for "tomorrow" but would silently
    discard the time on a reminder_at of "2026-12-01T09:30:00".

    Raises on an unparseable non-empty string, so a typo becomes a 422 rather
    than a silently dropped date - which is what the endpoints used to do when
    parse_relative_date() returned None.
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return ensure_aware(value)

    if not isinstance(value, str):
        raise ValueError(f"Expected a date string or datetime, got {type(value).__name__}")

    text = value.strip()
    if not text:
        return None

    # ISO first, to keep any time component the caller supplied.
    try:
        return ensure_aware(datetime.fromisoformat(text))
    except ValueError:
        pass

    # Then relative phrases, which resolve to midnight by definition.
    parsed = parse_relative_date(text)
    if parsed is None:
        raise ValueError(
            f"Could not interpret '{value}' as a date. "
            "Use an ISO 8601 date or a phrase like 'tomorrow' or 'next friday'."
        )
    return parsed


# A contact category that must be one of the ContactCategory values.
CategoryField = Annotated[str | None, BeforeValidator(_validate_category)]

# A datetime accepting ISO strings and relative phrases, normalized to aware.
FlexibleDateTime = Annotated[datetime | None, BeforeValidator(_validate_flexible_datetime)]
