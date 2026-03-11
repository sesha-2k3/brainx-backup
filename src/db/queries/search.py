# Queries: Full-text search and filtered listing queries

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Contact, Interaction


def _escape_like(value: str) -> str:
    """
    Escape special characters for LIKE/ILIKE queries.
    
    Special characters in LIKE:
    - % matches any sequence of characters
    - _ matches any single character
    - \ is the escape character
    """
    return (
        value
        .replace("\\", "\\\\")  # Escape backslash first
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


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
    escaped_query = _escape_like(query_text.lower())
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
    since: Optional[datetime] = None,
    limit: int = 50,
) -> list[Contact]:
    """Get contacts filtered by category, optionally since a date."""
    query = select(Contact).where(
        Contact.tenant_id == tenant_id,
        Contact.category == category,  # Exact match, no LIKE needed
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
    since: Optional[datetime] = None,
    limit: int = 20,
) -> list[Interaction]:
    """Get interactions for contacts at a specific company."""
    if not company.strip():
        return []
    
    # Escape special characters for LIKE
    escaped_company = _escape_like(company)
    pattern = f"%{escaped_company}%"
    
    # First get contacts at this company
    contacts_result = await db.execute(
        select(Contact.id)
        .where(
            Contact.tenant_id == tenant_id,
            Contact.company.ilike(pattern, escape="\\"),
        )
    )
    contact_ids = [row[0] for row in contacts_result.fetchall()]
    
    if not contact_ids:
        return []
    
    # Get interactions for those contacts
    query = select(Interaction).where(
        Interaction.tenant_id == tenant_id,
        Interaction.contact_id.in_(contact_ids),
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
    now = datetime.now(timezone.utc)
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
    tenant_id: str = "default",  # Added tenant_id for security
    interaction_limit: int = 10,
) -> Optional[dict]:
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
            Interaction.tenant_id == tenant_id,  # Also filter interactions
        )
        .order_by(Interaction.occurred_at.desc())
        .limit(interaction_limit)
    )
    interactions = list(interactions_result.scalars().all())
    
    return {
        "contact": contact,
        "interactions": interactions,
    }