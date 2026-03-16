# Queries: Full-text search and filtered listing queries

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Contact, Interaction
from src.utils.text import escape_like


async def search_all(
    db: AsyncSession,
    query_text: str,
    tenant_id: str = "default",
    limit: int = 20,
) -> dict:
    """
    Search across contacts and interactions.
    Returns dict with 'contacts' and 'interactions' lists.
    """
    if not query_text.strip():
        return {"contacts": [], "interactions": []}

    # Escape special characters and prepare pattern
    escaped_query = escape_like(query_text.lower())
    pattern = f"%{escaped_query}%"

    # Search contacts
    contacts_result = await db.execute(
        select(Contact)
        .where(
            Contact.tenant_id == tenant_id,
            Contact.search_vector.ilike(pattern, escape="\\"),
        )
        .order_by(Contact.updated_at.desc())
        .limit(limit)
    )
    contacts = list(contacts_result.scalars().all())

    # Search interactions
    interactions_result = await db.execute(
        select(Interaction)
        .where(
            Interaction.tenant_id == tenant_id,
            Interaction.search_vector.ilike(pattern, escape="\\"),
        )
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
    tenant_id: str = "default",
    since: datetime | None = None,
    limit: int = 50,
) -> list[Contact]:
    """Get contacts filtered by category, optionally since a date."""
    query = select(Contact).where(
        Contact.tenant_id == tenant_id,
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
    tenant_id: str = "default",
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
            Contact.tenant_id == tenant_id,
            Contact.company.ilike(pattern, escape="\\"),
        )
        .scalar_subquery()
    )

    # Build interactions query using subquery
    query = select(Interaction).where(
        Interaction.tenant_id == tenant_id,
        Interaction.contact_id.in_(contact_subq),
    )

    if since:
        query = query.where(Interaction.occurred_at >= since)

    query = query.order_by(Interaction.occurred_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_recent_activity(
    db: AsyncSession,
    tenant_id: str = "default",
    days: int = 7,
    limit: int = 50,
) -> list[Interaction]:
    """Get all interactions from the last N days."""
    now = datetime.now(UTC)
    since = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)

    result = await db.execute(
        select(Interaction)
        .where(
            Interaction.tenant_id == tenant_id,
            Interaction.occurred_at >= since,
        )
        .order_by(Interaction.occurred_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_contact_with_interactions(
    db: AsyncSession,
    contact_id: str,
    tenant_id: str = "default",
    interaction_limit: int = 10,
) -> dict | None:
    """Get a contact with their recent interactions."""
    # Fetch with tenant_id check to prevent cross-tenant access
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == tenant_id,
        )
    )
    contact = result.scalar_one_or_none()

    if not contact:
        return None

    interactions_result = await db.execute(
        select(Interaction)
        .where(
            Interaction.contact_id == contact_id,
            Interaction.tenant_id == tenant_id,
        )
        .order_by(Interaction.occurred_at.desc())
        .limit(interaction_limit)
    )
    interactions = list(interactions_result.scalars().all())

    return {
        "contact": contact,
        "interactions": interactions,
    }
