"""
Queries: Reusable SQL filter builders

Lives here rather than in src/utils/text.py on purpose: this module builds
SQLAlchemy expressions, and utils/text.py is pure-logic (its tests run with
zero doubles and no DB import). Keeping the layering intact.
"""

from sqlalchemy import ColumnElement, and_, or_
from sqlalchemy.orm import InstrumentedAttribute

from src.utils.text import escape_like


def match_all_terms(
    query_text: str,
    *columns: InstrumentedAttribute,
) -> ColumnElement[bool] | None:
    """
    Build a filter where EVERY whitespace-separated term in `query_text` must
    appear (as a substring, case-insensitively) in AT LEAST ONE of `columns`.

    So searching "smith acme" against (name, company) matches a contact named
    "John Smith" at "Acme Corp" — each term is found in some column, though
    neither column contains the whole phrase.

    This replaces the old denormalized `search_vector` TEXT column, which was
    a lowercased concatenation of these same fields substring-matched with a
    single ILIKE. That column was never actually added to the models or to any
    migration, so every write to it silently vanished and every read from it
    would have raised AttributeError.

    Returns None for a blank query so callers can decide what an empty search
    means rather than being handed a filter that matches everything.
    """
    terms = query_text.split()
    if not terms or not columns:
        return None

    return and_(
        *[
            or_(*[col.ilike(f"%{escape_like(term)}%", escape="\\") for col in columns])
            for term in terms
        ]
    )
