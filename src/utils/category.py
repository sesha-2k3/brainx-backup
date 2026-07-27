# Utils: Deterministic contact-category classification
#
# Two jobs:
#   1. match_category_keywords() - try to classify from obvious keywords
#      *before* ever calling the LLM. If this hits, we never let the LLM's
#      free-text guess overwrite it.
#   2. clamp_category() - if the LLM did have to guess (no keyword match),
#      validate its output against the enum instead of trusting it verbatim.
#      A value that isn't a real category becomes None, never a hallucinated
#      string written to the database.
#
# NOTE: adjust this import to wherever ContactCategory actually lives in your
# tree (it wasn't in the files I had visibility into - I only saw the enum's
# own definition, not what imports it). Likely one of:
#   from src.db.models import ContactCategory
#   from src.schemas.contacts import ContactCategory
import re

from src.schemas.contact_category_enums import ContactCategory  # ADJUST PATH

# Keep these tight and high-precision. A false keyword match is worse than
# falling through to the LLM, since it silently overrides whatever the LLM
# (or the user, later, on the confirm screen) would have said.
_CATEGORY_KEYWORDS: dict[ContactCategory, tuple[str, ...]] = {
    ContactCategory.INVESTOR: ("investor", "vc", "venture capital", "angel investor"),
    ContactCategory.CLIENT: ("client", "customer"),
    ContactCategory.PARTNER: ("co-founder", "cofounder", "business partner"),
    ContactCategory.FAMILY: (
        "wife",
        "husband",
        "mother",
        "father",
        "sister",
        "brother",
        "cousin",
        "aunt",
        "uncle",
        "my son",
        "my daughter",
    ),
    ContactCategory.FRIEND: ("my friend", "old friend", "buddy"),
    ContactCategory.COLLEAGUE: ("colleague", "coworker", "co-worker", "teammate"),
}


def match_category_keywords(text: str) -> ContactCategory | None:
    """
    Return a category if a clear keyword match is found in free text, else
    None. Checked before the LLM is asked to classify at all.
    """
    if not text:
        return None

    lowered = text.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", lowered):
                return category

    return None


def clamp_category(value: str | None) -> str | None:
    """
    Validate a category string (e.g. from an LLM response) against the enum.
    Returns None instead of raising or passing through an invalid value -
    this is what prevents a hallucinated category from ever reaching the DB.
    """
    if not value:
        return None

    try:
        return ContactCategory(value.strip().lower()).value
    except ValueError:
        return None
