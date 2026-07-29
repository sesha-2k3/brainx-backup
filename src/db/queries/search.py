# Queries: Full-text search and filtered listing queries

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Contact, Interaction
from src.db.queries.filters import match_all_terms
from src.utils.text import escape_like

# Columns that a free-text search looks through.
CONTACT_SEARCH_COLUMNS = (
    Contact.name,
    Contact.email,
    Contact.company,
    Contact.role,
    Contact.website,
    Contact.notes,
    Contact.context,
)

INTERACTION_SEARCH_COLUMNS = (
    Interaction.summary,
    Interaction.raw_transcript,
)


async def search_all(
    db: AsyncSession,
    query_text: str,
    limit: int = 20,
) -> dict:
    """
    Search across contacts and interactions.
    Returns dict with 'contacts' and 'interactions' lists.
    """
    contact_filter = match_all_terms(query_text, *CONTACT_SEARCH_COLUMNS)
    interaction_filter = match_all_terms(query_text, *INTERACTION_SEARCH_COLUMNS)

    if contact_filter is None or interaction_filter is None:
        return {"contacts": [], "interactions": []}

    # Search contacts (tenant filter applied automatically by TenantSession)
    contacts_result = await db.execute(
        select(Contact).where(contact_filter).order_by(Contact.updated_at.desc()).limit(limit)
    )
    contacts = list(contacts_result.scalars().all())

    # Search interactions
    interactions_result = await db.execute(
        select(Interaction)
        .where(interaction_filter)
        .order_by(Interaction.occurred_at.desc())
        .limit(limit)
    )
    interactions = list(interactions_result.scalars().all())

    return {
        "contacts": contacts,
        "interactions": interactions,
    }


async def get_contacts_by_category(
    db: AsyncSession,
    category: str,
    since: datetime | None = None,
    limit: int = 50,
) -> list[Contact]:
    """Get contacts filtered by category, optionally since a date."""
    query = select(Contact).where(
        Contact.category == category,
    )
    if since:
        query = query.where(Contact.updated_at >= since)
    query = query.order_by(Contact.updated_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_interactions_by_company(
    db: AsyncSession,
    company: str,
    since: datetime | None = None,
    limit: int = 20,
) -> list[Interaction]:
    """Get interactions for contacts at a specific company using subquery join."""
    if not company.strip():
        return []

    # Escape special characters for LIKE
    escaped_company = escape_like(company)
    pattern = f"%{escaped_company}%"

    # Use scalar subquery instead of fetching IDs into Python
    # This lets PostgreSQL optimize as a single query plan
    contact_subq = (
        select(Contact.id)
        .where(
            Contact.company.ilike(pattern, escape="\\"),
        )
        .scalar_subquery()
    )

    # Build interactions query using subquery
    query = select(Interaction).where(
        Interaction.contact_id.in_(contact_subq),
    )

    if since:
        query = query.where(Interaction.occurred_at >= since)

    query = query.order_by(Interaction.occurred_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_recent_activity(
    db: AsyncSession,
    days: int = 7,
    limit: int = 50,
) -> list[Interaction]:
    """Get all interactions from the last N days."""
    now = datetime.now(UTC)
    since = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)

    result = await db.execute(
        select(Interaction)
        .where(
            Interaction.occurred_at >= since,
        )
        .order_by(Interaction.occurred_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_contact_with_interactions(
    db: AsyncSession,
    contact_id: str,
    interaction_limit: int = 10,
) -> dict | None:
    """Get a contact with their recent interactions."""
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
        )
    )
    contact = result.scalar_one_or_none()

    if not contact:
        return None

    interactions_result = await db.execute(
        select(Interaction)
        .where(
            Interaction.contact_id == contact_id,
        )
        .order_by(Interaction.occurred_at.desc())
        .limit(interaction_limit)
    )
    interactions = list(interactions_result.scalars().all())

    return {
        "contact": contact,
        "interactions": interactions,
    }
